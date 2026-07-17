import asyncio
import datetime
import os.path
import random
import shutil
import string
import subprocess
import sys
import time

import aiohttp
import deepl
import discord
import pytz
from deepl import Language
from discord import Bot, ButtonStyle, File, Interaction, InteractionType, Message
from discord.ext import commands, tasks
from discord.ext.commands import BucketType, cooldown
from discord.ui import (
    ActionRow,
    Button,
    Container,
    DesignerView,
    MediaGallery,
    Section,
    Separator,
    TextDisplay,
    Thumbnail,
)
from markdownify import markdownify
from mastodon.return_types import Account, Poll, Status

from constants import (
    CHANNEL_MEMES,
    CHANNEL_MODERATION,
    DEEPL_API_KEY,
    FORGEJO_OWNER,
    FORGEJO_PROJECT,
    GUILD,
    OWNER,
    VERSION,
)
from database import engine
from logger import lunamon_logger
from util.akkoma import akkoma_cache
from util.keysmash_generator import keysmash_ai
from util.storage import get_data, set_data
from util.yuri_util import get_some_yuri

dm_cache = []

deepl_client = deepl.DeepLClient(DEEPL_API_KEY)


def generate_meow():
    meow = random.choice(["meow", "nya", "mraow", "mwrmmwra"])

    if meow == "nya":
        return "ny" + random.randint(1, 8) * "a"
    elif meow == "mwrmmwra":
        meow = "mr"
        for i in range(random.randint(4, 12)):
            meow += random.choice(["a", "w", "r"])

        return meow

    return meow


def generate_fluster():
    fluster_type = random.choice([">///<", "keysmash"])
    if fluster_type == ">///<":
        return ">" + "/" * random.randint(3, 10) + "<"
    elif fluster_type == "keysmash":
        return (
            "".join(random.choices(string.ascii_lowercase, k=random.randint(3, 25)))
            + " >"
            + "/" * random.randint(3, 10)
            + "<"
        )
    else:
        raise ValueError("Invalid fluster type")


class RefreshTimeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="refresh", style=discord.ButtonStyle.secondary, custom_id="refresh_time"
    )
    async def refresh_btn(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        try:
            utc = pytz.timezone("UTC")
            lunya_tz = pytz.timezone("Europe/Prague")

            utc_time = datetime.datetime.now(utc)
            lunya_time = datetime.datetime.now(lunya_tz)

            await interaction.edit(
                content=f"# Time\n"
                f"Current time for Lunya: {lunya_time.strftime('%a %d %b %Y, %H:%M:%S %Z (%z)')}\n"
                f"Server clock: {utc_time.strftime('%a %d %b %Y, %H:%M:%S %Z (%z)')}\n"
                f"Your time: <t:{int(utc_time.timestamp())}:F>"
            )
        except Exception:
            lunamon_logger.exception("An error occurred:")
            await interaction.response.send_message("error :(", ephemeral=True)


class ReadReceiptComponent(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Mark as read",
        style=discord.ButtonStyle.primary,
        custom_id="read_receipt",
    )
    async def mark_as_read(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        try:
            data = get_data(f"read_receipt/{interaction.message.id}")

            if "readUsers" not in data:
                data["readUsers"] = []

            if "message" not in data:
                data["message"] = interaction.message.content

            if str(interaction.user.id) in data["readUsers"]:
                await interaction.respond(
                    "already marked as read! thank you <3", ephemeral=True
                )
                return

            data["readUsers"].append(str(interaction.user.id))

            await interaction.edit(
                content=f"{data['message']}\n*Read by {', '.join([f'<@{i}>' for i in data['readUsers']])}*"
            )
            set_data(f"read_receipt/{interaction.message.id}", data)
        except Exception:
            lunamon_logger.exception("An error occurred:")
            await interaction.respond(
                "error :(\n-# this error was automatically reported", ephemeral=True
            )


class PickerComponent(discord.ui.View):
    def __init__(self, type: str):
        super().__init__(timeout=None)

        if type == "meow":
            meow_btn = discord.ui.Button(
                style=discord.ButtonStyle.primary, label="Meow", custom_id="picker_meow"
            )
            meow_btn.callback = self.meow
            self.add_item(meow_btn)
        elif type == ":3":
            colon_three_button = discord.ui.Button(
                style=discord.ButtonStyle.primary,
                label=":3",
                custom_id="picker_colon_three",
            )
            colon_three_button.callback = self.colon_three
            self.add_item(colon_three_button)
        elif type == "compliments":
            # cute
            cute_button = discord.ui.Button(
                style=discord.ButtonStyle.primary,
                label="such a cute girl~ :3",
                custom_id="picker_cute",
            )
            cute_button.callback = self.cute
            self.add_item(cute_button)

            # pretty
            pretty_button = discord.ui.Button(
                style=discord.ButtonStyle.primary,
                label="such a pretty girl~ :3",
                custom_id="picker_pretty",
            )
            pretty_button.callback = self.pretty
            self.add_item(pretty_button)

            # gorgeous

            gorgeous_button = discord.ui.Button(
                style=discord.ButtonStyle.primary,
                label="such a gorgeous girl :3",
                custom_id="picker_gorgeous",
            )
            gorgeous_button.callback = self.gorgeous
            self.add_item(gorgeous_button)

            # cool

            cool_button = discord.ui.Button(
                style=discord.ButtonStyle.primary,
                label="such a cool girl~ :3",
                custom_id="picker_cool",
            )
            cool_button.callback = self.cool
            self.add_item(cool_button)

            # good girl

            good_girl_button = discord.ui.Button(
                style=discord.ButtonStyle.primary,
                label="such a goooood girl~ :3",
                custom_id="picker_good_girl",
            )
            good_girl_button.callback = self.good_girl
            self.add_item(good_girl_button)
        elif type == "meowat":
            meow_at_button = discord.ui.Button(
                style=discord.ButtonStyle.primary,
                label="meow at Lunya :3",
                custom_id="picker_meow_at",
            )
            meow_at_button.callback = self.meowat
            self.add_item(meow_at_button)
        elif type == "purrr":
            purrr_button = discord.ui.Button(
                style=discord.ButtonStyle.primary,
                label="purrr :3",
                custom_id="picker_purrr",
            )
            purrr_button.callback = self.purrr
            self.add_item(purrr_button)
        elif type == "girlkiss":
            girlkiss_button = discord.ui.Button(
                style=discord.ButtonStyle.primary,
                label="girlkiss a girl Lunya :3 (real) UwU",
                custom_id="picker_girlkiss",
            )
            girlkiss_button.callback = self.girlkiss
            self.add_item(girlkiss_button)
        elif type == "boop":
            boop_button = discord.ui.Button(
                style=discord.ButtonStyle.primary,
                label="boop :3",
                custom_id="picker_boop",
            )
            boop_button.callback = self.boop
            self.add_item(boop_button)
        elif type == "paws":
            paws_at_you_button = discord.ui.Button(
                style=discord.ButtonStyle.primary,
                label="*paws at you*",
                custom_id="picker_paws",
            )
            paws_at_you_button.callback = self.paws_at_you
            self.add_item(paws_at_you_button)
        elif type == "click":
            self.click_button = discord.ui.Button(
                style=discord.ButtonStyle.primary,
                label="*click click*",
                custom_id="picker_click",
            )
            self.click_button.callback = self.click
            self.add_item(self.click_button)
        elif type == "beep":
            self.click_button = discord.ui.Button(
                style=discord.ButtonStyle.primary,
                label="beeeeep",
                custom_id="picker_beep",
            )
            self.click_button.callback = self.beep
            self.add_item(self.click_button)
        else:
            raise ValueError("Invalid type")

    async def meow(self, interaction: discord.Interaction):
        try:
            meow = generate_meow()
            await interaction.respond(f"✅ Message sent\n{meow} :3", ephemeral=True)
            dm_cache.append(f"{meow} by {interaction.user.mention} :3")
        except Exception:
            lunamon_logger.exception("An error occurred:")
            await interaction.respond("An error occurred", ephemeral=True)

    async def colon_three(self, interaction: discord.Interaction):
        try:
            colon_three = ":" + "3" * random.randint(4, 12)
            await interaction.respond(
                f"✅ Message sent\n:{colon_three} :3", ephemeral=True
            )
            dm_cache.append(f"{colon_three} by {interaction.user.mention} :3")
        except Exception:
            lunamon_logger.exception("An error occurred:")
            await interaction.respond("An error occurred", ephemeral=True)

    async def cute(self, interaction: discord.Interaction):
        try:
            await interaction.respond(f"✅ {generate_fluster()}", ephemeral=True)
            dm_cache.append(
                f"{interaction.user.mention} said that you're such a cute girl~ :3"
            )
        except Exception:
            lunamon_logger.exception("An error occurred:")
            await interaction.respond("An error occurred", ephemeral=True)

    async def pretty(self, interaction: discord.Interaction):
        try:
            await interaction.respond(f"✅ {generate_fluster()}", ephemeral=True)
            dm_cache.append(
                f"{interaction.user.mention} said that you're such a pretty girl~ :3"
            )
        except Exception:
            lunamon_logger.exception("An error occurred:")
            await interaction.respond("An error occurred", ephemeral=True)

    async def gorgeous(self, interaction: discord.Interaction):
        try:
            await interaction.respond(f"✅ {generate_fluster()}", ephemeral=True)
            dm_cache.append(
                f"{interaction.user.mention} said that you're such a gorgeous girl~ :3"
            )
        except Exception:
            lunamon_logger.exception("An error occurred:")
            await interaction.respond("An error occurred", ephemeral=True)

    async def cool(self, interaction: discord.Interaction):
        try:
            await interaction.respond(f"✅ {generate_fluster()}", ephemeral=True)
            dm_cache.append(
                f"{interaction.user.mention} said that you're such a coool girl~ :3"
            )
        except Exception:
            lunamon_logger.exception("An error occurred:")
            await interaction.respond("An error occurred", ephemeral=True)

    async def good_girl(self, interaction: discord.Interaction):
        try:
            await interaction.respond(
                f"✅ {generate_fluster()} {generate_fluster()}", ephemeral=True
            )
            dm_cache.append(
                f"{interaction.user.mention} said that you're such a goooood girl~ :3"
            )
        except Exception:
            lunamon_logger.exception("An error occurred:")
            await interaction.respond("An error occurred", ephemeral=True)

    async def meowat(self, interaction: discord.Interaction):
        try:
            await interaction.respond(f"✅ meow -> <@{OWNER}>", ephemeral=True)
            dm_cache.append(f"{interaction.user.mention} meowd at you :3")
        except Exception:
            lunamon_logger.exception("An error occurred:")
            await interaction.respond("An error occurred", ephemeral=True)

    async def purrr(self, interaction: discord.Interaction):
        try:
            await interaction.respond("✅ *purrrrrrr*", ephemeral=True)
            dm_cache.append(f"{interaction.user.mention} has *purrrrr* :3")
        except Exception:
            lunamon_logger.exception("An error occurred:")
            await interaction.respond("An error occurred", ephemeral=True)

    async def girlkiss(self, interaction: discord.Interaction):
        try:
            await interaction.respond("✅ Girls were kissed :3", ephemeral=True)
            dm_cache.append(
                f"{interaction.user.mention} has give you girlkiss :3333333333"
            )
        except Exception:
            lunamon_logger.exception("An error occurred:")
            await interaction.respond("An error occurred", ephemeral=True)

    async def boop(self, interaction: discord.Interaction):
        try:
            await interaction.respond("✅ >///<", ephemeral=True)
            dm_cache.append(f"{interaction.user.mention} has booped you :3")
        except Exception:
            lunamon_logger.exception("An error occurred:")
            await interaction.respond("An error occurred", ephemeral=True)

    async def paws_at_you(self, interaction: discord.Interaction):
        try:
            await interaction.respond("✅ *paws at Lunya*", ephemeral=True)
            dm_cache.append(f"{interaction.user.mention} *paws at you* :3")
        except Exception:
            lunamon_logger.exception("An error occurred:")
            await interaction.respond("An error occurred", ephemeral=True)

    async def beep(self, interaction: discord.Interaction):
        try:
            await interaction.respond("✅ beeeeep", ephemeral=True)
            dm_cache.append(f"{interaction.user.mention} beeped at you :3")
        except Exception:
            lunamon_logger.exception("An error occurred:")
            await interaction.respond("An error occurred", ephemeral=True)

    async def click(self, interaction: discord.Interaction):
        try:
            await interaction.respond("✅ *click click* at Lunya", ephemeral=True)

            click_data = get_data("clicker")
            # total
            if "total" not in click_data:
                click_data["total"] = 0

            click_data["total"] += 1

            # per user
            if "from" not in click_data:
                click_data["from"] = {}

            if str(interaction.user.id) not in click_data["from"]:
                click_data["from"][str(interaction.user.id)] = 0

            click_data["from"][str(interaction.user.id)] += 1

            set_data("clicker", click_data)

            dm_cache.append(f"{interaction.user.mention} clicked at you :3")
        except Exception:
            lunamon_logger.exception("An error occurred:")
            await interaction.respond("An error occurred", ephemeral=True)


def generate_user_embed(account: Account):
    desc_start = markdownify(account.note)
    desc = desc_start[:1500]
    if desc != desc_start:
        desc = desc + "..."

    emb = discord.Embed(
        title=f"{account.display_name} ({account.acct})",
        description=desc,
        thumbnail=account.avatar,
        fields=[
            discord.EmbedField(
                name="Statuses", value=str(account.statuses_count), inline=True
            ),
            discord.EmbedField(
                name="Followers", value=str(account.followers_count), inline=True
            ),
            discord.EmbedField(
                name="Following", value=str(account.following_count), inline=True
            ),
        ],
        url=account.url,
        color=discord.Color.from_rgb(255, 119, 255),
    )

    if "@" in account.acct:
        emb.set_footer(
            text="The information may not be accurate as it comes from a remote instance."
        )

    return emb


def generate_status_embed(status: Status, pinned=False):
    image_url = (
        status.media_attachments[0].url
        if len(status.media_attachments) > 0 and len(status.spoiler_text) == 0
        else None
    )

    reaction_string = ""

    if status.favourites_count > 0:
        reaction_string += f"{status.favourites_count} favorites | "
    if status.replies_count > 0:
        reaction_string += f"{status.replies_count} replies | "
    if status.reblogs_count > 0:
        reaction_string += f"{status.reblogs_count} reblogs | "

    reaction_string = reaction_string[:-3]

    pinned_post = "Pinned post by " if pinned else ""

    content = markdownify(status.content)
    desc = (
        content if len(status.spoiler_text) == 0 else f"CW: {status.spoiler_text}\n\n"
    )

    if len(status.spoiler_text) > 0:
        if len(status.media_attachments) > 0 and len(content) > 0:
            desc += "(Open the link in order to view the text and media)"
        elif len(status.media_attachments) > 0 and len(content) == 0:
            desc += "(Open the link in order to view the media)"
        else:
            desc += "(Open the link in order to view the text)"

    if status.poll is not None:
        desc += get_poll_str(status.poll)

    emb = discord.Embed(
        title=f"{'Pinned ' if pinned else ''}Note by {status.account.display_name} ({status.account.acct})",
        url=status.url,
        description=desc[:1500],
        image=image_url,
        author=discord.EmbedAuthor(
            name=f"{pinned_post}{status.account.display_name} ({status.account.acct})",
            icon_url=status.account.avatar,
            url=status.account.url,
        ),
        color=discord.Color.from_rgb(255, 119, 255),
        footer=discord.EmbedFooter(text=reaction_string)
        if len(reaction_string) > 0
        else None,
    )

    return emb


async def get_posts_under_hashtags(hashtag) -> list[discord.Embed] | None:
    # Lookup_str: #art for example
    embeds = []

    hashtag = list(akkoma_cache.client.timeline_hashtag(hashtag))

    for i in hashtag[3:]:
        embeds.append(generate_status_embed(i))

    return embeds


def get_poll_str(poll: Poll) -> str:
    message = "\n\n**[Poll]**\n"
    counts = poll.votes_count

    for option in poll.options:
        if counts == 0 or option.votes_count is None:
            message += f"**{option.title}** - {option.votes_count} votes\n"
        else:
            message += f"**{option.title}** - {option.votes_count} votes ({int(option.votes_count / counts * 100)}%)\n"

    message += "\n"

    if poll.multiple:
        message += "**Multiple Choices** - "

    expires_at = poll.expires_at
    if expires_at is not None:
        message += f"**Expires at {expires_at.strftime('%Y/%m/%d %H:%M:%S %Z')}**\n"

    return message.rstrip()


async def search(
    query: str, content_type: str, media_type: str, count: int
) -> tuple[list[discord.Embed], int] | None:
    start_time = time.time()
    if content_type == "posts":
        return await search_posts(query, media_type, start_time, count)
    elif content_type == "users":
        return await search_users(query, start_time, count)

    raise ValueError(
        f"content_type is out of range: {content_type} is not a valid value"
    )


async def search_users(query, start_time, count):
    users = akkoma_cache.client.search_v2(query)
    embeds = []

    for i in users.accounts:
        emb = generate_user_embed(i)

        if emb is None:
            continue

        embeds.append(emb)

        if len(embeds) >= count:
            break

    end_time = time.time()
    diff = round((end_time - start_time) * 1000)
    return (embeds, diff) if len(embeds) > 0 else None


async def search_posts(query, media_type, start_time, count):
    statuses = akkoma_cache.client.search_v2(query)
    embeds = []

    for i in statuses.statuses:
        if len(i.spoiler_text) > 0:
            continue
        if media_type == "image" and not any(
            j.type == "image" for j in i.media_attachments
        ):
            continue
        if media_type == "video" and not any(
            j.type == "video" for j in i.media_attachments
        ):
            continue

        emb = generate_status_embed(i)
        embeds.append(emb)

        if len(embeds) >= count:
            break

    end_time = time.time()
    diff = round((end_time - start_time) * 1000)
    return (embeds[:count], diff) if len(embeds) > 0 else None


async def uwuify(text: str) -> str | None:
    # Send request
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=1)) as session:
        async with session.post(
            "https://uwu.pm/api/v1/uwu", json={"text": text, "provider": "uwwwupp"}
        ) as res:
            if res.status != 200:
                return None

            res = await res.json()

            if "uwu" not in res or res["uwu"] is None:
                return None

            return res["uwu"]


class UserCommands(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.target_language = Language.ENGLISH_AMERICAN

    @discord.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(PickerComponent("meow"))
        self.bot.add_view(PickerComponent(":3"))
        self.bot.add_view(PickerComponent("compliments"))
        self.bot.add_view(PickerComponent("meowat"))
        self.bot.add_view(PickerComponent("purrr"))
        self.bot.add_view(PickerComponent("girlkiss"))
        self.bot.add_view(PickerComponent("boop"))
        self.bot.add_view(PickerComponent("paws"))
        self.bot.add_view(PickerComponent("click"))
        self.bot.add_view(ReadReceiptComponent())
        self.bot.add_view(RefreshTimeView())
        self.handle_queue.start()

    @discord.Cog.listener()
    async def on_interaction(self, interaction: Interaction):
        if (
            interaction.custom_id == "more_yuri_pwease_uwu"
            and interaction.type == InteractionType.component
        ):
            with engine.begin() as c:
                yuri_filename, yuri_source = get_some_yuri(c)

            gallery = MediaGallery()
            gallery.add_item(f"attachment://{yuri_filename.split('/')[-1]}")

            container = Container()
            container.add_item(gallery)
            container.add_item(Separator())
            container.add_item(
                ActionRow(
                    Button(
                        label="more yuri :3",
                        style=ButtonStyle.primary,
                        custom_id="more_yuri_pwease_uwu",
                    ),
                    Button(
                        label="source",
                        style=ButtonStyle.link,
                        url=yuri_source,
                    ),
                )
            )

            await interaction.respond(
                view=DesignerView(container),
                file=File(yuri_filename),
            )

    user_commands = discord.SlashCommandGroup(
        name="user",
        description="User commands",
        integration_types=[discord.IntegrationType.user_install],
    )

    @user_commands.command(
        name="ping",
        description="Tests connection to Discord",
        integration_types=[discord.IntegrationType.user_install],
    )
    async def ping(self, ctx: discord.ApplicationContext):
        await ctx.respond(
            f"Pong! {self.bot.latency * 1500} ms", ephemeral=(ctx.user.id != int(OWNER))
        )

    @user_commands.command(
        name="message",
        description="Send message as bot",
        integration_types=[discord.IntegrationType.user_install],
    )
    async def message(self, ctx: discord.ApplicationContext, msg: str):
        try:
            if ctx.user.id != int(OWNER):
                await ctx.respond(
                    "You are not authorized to use this command!", ephemeral=True
                )
                return

            await ctx.respond(msg)
        except Exception:
            lunamon_logger.exception("Error occured in /user message")

    @user_commands.command(
        name="information",
        description="Print information about the server",
        integration_types=[discord.IntegrationType.user_install],
    )
    async def information(self, ctx: discord.ApplicationContext, public: bool = False):
        try:
            if ctx.user.id != int(OWNER):
                await ctx.respond(
                    "You are not authorized to use this command!", ephemeral=True
                )
                return

            uname = subprocess.run(
                ["uname", "-snrvmpio"], capture_output=True, text=True
            )
            uptime = subprocess.run(["uptime"], capture_output=True, text=True)
            version = (
                f"Python {sys.version} on {sys.platform}\n"
                f"py-cord {discord.__version__}\n"
            )

            await ctx.respond(
                f"# Lunamon version {VERSION}\n"
                f"```\n"
                f"{uname.stdout.strip()}\n"
                f"{uptime.stdout.strip()}\n"
                f"{version}"
                f"```",
                ephemeral=not public,
            )
        except Exception:
            lunamon_logger.exception("Error occured in /user information")
            await ctx.respond(
                "An error occurred while executing the command.", ephemeral=True
            )

    @user_commands.command(name="picker")
    async def picker(
        self,
        ctx: discord.ApplicationContext,
        message: str,
        type: discord.Option(
            str,
            choices=[
                "meow",
                ":3",
                "compliments",
                "meowat",
                "purrr",
                "girlkiss",
                "boop",
                "paws",
                "click",
                "beep",
            ],
        ),
    ):
        try:
            if ctx.user.id != int(OWNER):
                await ctx.respond(
                    "You are not authorized to use this command!", ephemeral=True
                )
                return

            await ctx.respond(message, view=PickerComponent(type))
        except Exception:
            lunamon_logger.exception("Error occured in /user picker")
            await ctx.respond(
                "An error occurred while executing the command.", ephemeral=True
            )

    @user_commands.command(
        name="clicker_counts", description="how many times did i click at you?"
    )
    async def clicker_counts(
        self,
        ctx: discord.ApplicationContext,
        from_user: discord.User = None,
        public: bool = False,
    ):
        try:
            if ctx.user.id != int(OWNER):
                await ctx.respond(
                    "You are not authorized to use this command!", ephemeral=True
                )
                return

            click_data = get_data("clicker")

            if "total" not in click_data:
                click_data["total"] = 0
            if "from" not in click_data:
                click_data["from"] = {}

            if from_user is None:
                await ctx.respond(
                    f"a total of {click_data['total']} clicks has been done at you :3",
                    ephemeral=not public,
                )
                return

            if str(from_user.id) in click_data["from"]:
                await ctx.respond(
                    f"a total of {click_data['total']} clicks and {click_data['from'][str(from_user.id)]} clicks specifically from {from_user.mention} have been performed at you :3",
                    ephemeral=not public,
                )
            else:
                await ctx.respond(
                    f"a total of {click_data['total']} clicks has been done at you :3\n"
                    f"-# from user not found in db",
                    ephemeral=not public,
                )
        except Exception:
            lunamon_logger.exception("Error occured in /user clicker")
            await ctx.respond(
                "an error occurred while executing the command.", ephemeral=True
            )

    @user_commands.command(
        name="read_receipt",
        description="Send read receipt message which allows well accepting a read receipt",
    )
    async def read_receipt(self, ctx: discord.ApplicationContext, message: str):
        try:
            if ctx.user.id != int(OWNER):
                await ctx.respond(
                    "You are not authorized to use this command!", ephemeral=True
                )
                return

            await ctx.respond(message, view=ReadReceiptComponent())
        except Exception:
            lunamon_logger.exception("Error occured in /user read_receipt")
            await ctx.respond(
                "An error occurred while executing the command.", ephemeral=True
            )

    @user_commands.command(name="time", description="Get time for Lunya :3")
    async def time(self, ctx: discord.ApplicationContext):
        try:
            if ctx.user.id != int(OWNER):
                await ctx.respond(
                    "You are not authorized to use this command!", ephemeral=True
                )
                return

            utc = pytz.timezone("UTC")
            lunya_tz = pytz.timezone("Europe/Prague")

            utc_time = datetime.datetime.now(utc)
            lunya_time = datetime.datetime.now(lunya_tz)

            await ctx.respond(
                f"# Time\n"
                f"Current time for Lunya: {lunya_time.strftime('%a %d %b %Y, %H:%M:%S %Z (%z)')}\n"
                f"Server clock: {utc_time.strftime('%a %d %b %Y, %H:%M:%S %Z (%z)')}\n"
                f"Your time: <t:{int(utc_time.timestamp())}:F>",
                view=RefreshTimeView(),
            )
        except Exception:
            lunamon_logger.exception("Error occured in /user time")
            await ctx.respond(
                "An error occurred while executing the command.", ephemeral=True
            )

    fedi_group = discord.SlashCommandGroup(
        name="fedi",
        description="Fedi commands",
        integration_types=[discord.IntegrationType.user_install],
    )

    @fedi_group.command(
        name="search",
        description="Search on fedi",
        integration_types=[discord.IntegrationType.user_install],
    )
    @discord.option(name="media_type", choices=["image", "video"])
    @discord.option(name="content_type", choices=["posts", "users"])
    @discord.option(name="count", min=1, max=10)
    async def search(
        self,
        ctx: discord.ApplicationContext,
        q: str,
        content_type: str = "posts",
        media_type: str = "all",
        count: int = 3,
    ):
        try:
            # Verify right user
            if ctx.user.id != int(OWNER):
                await ctx.respond(
                    "You are not authorized to use this command!", ephemeral=True
                )
                return

            await ctx.defer()

            # Let's attempt to generate embed based on search function
            emb = await search(q, content_type, media_type, count)

            if emb is None:
                await ctx.followup.send("Error! No result")
                return

            await ctx.followup.send(
                embeds=emb[0], content=f"Searching finished in {emb[1]} ms"
            )
        except Exception as e:
            lunamon_logger.exception("An error occurred:")
            await ctx.followup.send(f"Error! Server error: {e=}")

    @fedi_group.command(
        name="post",
        description="Create a post on fedi",
        integration_types=[discord.IntegrationType.user_install],
    )
    @discord.option(name="visibility", choices=["public", "unlisted", "private"])
    async def post(
        self,
        ctx: discord.ApplicationContext,
        text: str,
        cw: str = "",
        visibility: str = "public",
        public_response: bool = False,
    ):
        try:
            post = akkoma_cache.client.status_post(
                text, spoiler_text=cw, visibility=visibility
            )
            await ctx.respond(
                f"Post created! {post.url}",
                ephemeral=not public_response,
            )
        except Exception:
            lunamon_logger.exception("An error occurred:")
            await ctx.respond("Failed to create status :(", ephemeral=True)

    @discord.message_command(
        name="post this on fedi",
        integration_types=[discord.IntegrationType.user_install],
    )
    @cooldown(1, 10, BucketType.default)
    async def post_message(self, ctx: discord.ApplicationContext, message: Message):
        try:
            owner = self.bot.get_user(int(OWNER))
            await ctx.respond("posting to fedi. see dms for activity", ephemeral=True)

            # get files
            if not os.path.exists("temp"):
                os.mkdir("temp")

            async def get_file(a: discord.Attachment):
                async with aiohttp.ClientSession() as sess:
                    async with sess.get(a.url) as req:
                        content = await req.read()
                        with open(f"temp/{a.filename}", "wb") as f:
                            f.write(content)

            await asyncio.gather(*[get_file(i) for i in message.attachments])

            media_ids = []

            if len(message.attachments) > 0:
                for i in message.attachments:
                    await owner.send(f"Alt text for {i.filename} ({i.url}):")
                    resp = await self.bot.wait_for(
                        "message", check=lambda msg: msg.author == owner
                    )

                    media_ids.append(
                        akkoma_cache.client.media_post(
                            f"temp/{i.filename}", description=resp.content
                        )
                    )

            cw = ""
            text = message.content

            # edits
            while True:
                await owner.send(
                    "post is ready to be created, please issue following commands if needed: [edit content, edit cw, no media, no content, post]"
                )
                resp = await self.bot.wait_for(
                    "message", check=lambda msg: msg.author == owner
                )

                if resp.content == "edit content":
                    await owner.send("new content:")
                    resp = await self.bot.wait_for(
                        "message", check=lambda msg: msg.author == owner
                    )

                    text = resp.content
                    await resp.add_reaction("✅")
                elif resp.content == "edit cw":
                    await owner.send("new cw:")
                    resp = await self.bot.wait_for(
                        "message", check=lambda msg: msg.author == owner
                    )

                    cw = resp.content
                    await resp.add_reaction("✅")
                elif resp.content == "no cw":
                    cw = ""
                    await resp.add_reaction("✅")
                elif resp.content == "no media":
                    media_ids = []
                    if os.path.exists("temp"):
                        for i in message.attachments:
                            os.unlink(f"temp/{i.filename}")

                        if len(os.listdir("temp")) == 0:
                            os.rmdir("temp")

                    await resp.add_reaction("✅")
                elif resp.content == "no content":
                    text = ""
                    await resp.add_reaction("✅")
                elif resp.content == "post":
                    if len(text) == 0 and len(media_ids) == 0:
                        await owner.send(
                            "failed to post: no text AND media found, at least one is needed"
                        )
                        return

                    break
                elif resp.content == "cancel":
                    await owner.send("canceling")
                    return

            status = akkoma_cache.client.status_post(
                text, media_ids=media_ids, spoiler_text=cw
            )

            await owner.send(f"post stolen\n{status.url or status.uri}")

            if os.path.exists("temp"):
                for i in message.attachments:
                    os.unlink(f"temp/{i.filename}")

                if len(os.listdir("temp")) == 0:
                    os.rmdir("temp")
        except Exception:
            lunamon_logger.exception("An error occurred:")
            await ctx.respond("Failed to create post :(", ephemeral=True)

    @user_commands.command(
        name="ban_from_lunya",
        description="Ban user from Lunya's Discord server",
        integration_types=[discord.IntegrationType.user_install],
    )
    async def ban_from_lunya(
        self, ctx: discord.ApplicationContext, user: discord.User, reason: str
    ):
        try:
            # Verify right user
            if ctx.user.id != int(OWNER):
                await ctx.respond(
                    "You are not authorized to use this command!", ephemeral=True
                )
                return

            # Get guild

            guild = self.bot.get_guild(int(GUILD))

            # Ban user

            a = guild.ban(user, reason=reason, delete_message_seconds=7 * 24 * 3600)

            # Log message

            logs_channel = guild.get_channel(int(CHANNEL_MODERATION))

            component = Container(
                TextDisplay("# Member Banned"),
                Separator(),
                TextDisplay(
                    "A member was banned externally using the user command by Lunya."
                ),
                Section(
                    TextDisplay("**User**: "),
                    TextDisplay(user.display_name),
                    accessory=Thumbnail(user.display_avatar.url),
                ),
            )

            b = logs_channel.send(view=DesignerView(component))

            c = ctx.respond("Member was banned successfully!", ephemeral=True)

            await asyncio.gather(a, b, c)
        except Exception:
            lunamon_logger.exception("Error occured from /user ban_from_lunya")
            await ctx.respond("An error occured banning this user.", ephemeral=True)

    @user_commands.command(
        name="uwwwu",
        description="UwUify text",
        integration_types=[discord.IntegrationType.user_install],
    )
    async def uwuify_text(
        self, ctx: discord.ApplicationContext, text: str, private: bool = True
    ):
        try:
            # Verify right user
            if ctx.user.id != int(OWNER):
                await ctx.respond(
                    "You are not authorized to use this command!", ephemeral=True
                )
                return

            # Send request
            uwuified = await uwuify(text)
            if uwuified is None:
                await ctx.respond("An error occured!", ephemeral=True)
                return

            await ctx.respond(uwuified, ephemeral=not private)
        except Exception as e:
            lunamon_logger.exception("Error occured in /user uwwwu")
            await ctx.respond(f"An error occured! {e=}", ephemeral=True)

    @discord.slash_command(name="uwuify", description="UwUify text")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def uwuify_text_public(
        self,
        ctx: discord.ApplicationContext,
        text: str,
        use_ai: discord.Option(
            bool,
            description="Do you want to use the latest cutting-edge AI to uwuify?",
            default=True,
        ),
    ):
        try:
            # Cutting-edge AI check
            if use_ai:
                await ctx.respond(keysmash_ai(), ephemeral=True)
                return

            # Send request
            uwuified = await uwuify(text)
            if uwuified is None:
                await ctx.respond("An error occured!", ephemeral=True)
                return

            await ctx.respond(uwuified, ephemeral=True)
        except Exception as e:
            lunamon_logger.exception("Error occured in the public uwuify text")
            await ctx.respond(f"An error occured! {e=}", ephemeral=True)

    @discord.message_command(
        name="Borrow Meme",
        description="Repost the message inside of the memes channel of Lunya's Discord server",
        integration_types=[discord.IntegrationType.user_install],
    )
    async def borrow_meme(
        self, ctx: discord.ApplicationContext, message: discord.Message
    ):
        try:
            if ctx.user.id != int(OWNER):
                await ctx.respond(
                    "You are not authorized to use this command!", ephemeral=True
                )
                return

            await ctx.respond("Meme will repost in Lunya server", ephemeral=True)

            # Download all attachments
            if not os.path.exists("temp"):
                os.mkdir("temp")

            for i in message.attachments:
                with open("temp/" + i.filename, "wb") as f:
                    await i.save(f)

            # Send it
            memes = self.bot.get_guild(int(GUILD)).get_channel(int(CHANNEL_MEMES))
            await memes.send(
                content=message.content,
                files=[
                    discord.File(f"temp/{i.filename}", i.filename)
                    for i in message.attachments
                ],
            )

            # Delete
            shutil.rmtree("temp")
        except Exception:
            lunamon_logger.exception("Error occured when borrowing a meme")
            await ctx.respond("Error!", ephemeral=True)

    @discord.slash_command(name="version", description="Print bot version")
    async def version(self, ctx: discord.ApplicationContext):
        try:
            await ctx.respond(
                f"# Lunamon version {VERSION}\n\n"
                f"Python {sys.version} on {sys.platform}\n"
                f"py-cord {discord.__version__}\n"
                f"Licensed under GNU AGPL v3.0. Software's source code is [here](<https://git.lunya.pet/{FORGEJO_OWNER}/{FORGEJO_PROJECT}>)",
                ephemeral=True,
            )
        except Exception:
            lunamon_logger.exception("Error occured when printing version, HOW????")
            await ctx.respond("Error!", ephemeral=True)

    @discord.slash_command(
        name="yuri",
        description="girls,,,, womeb,,,,",
        integration_types=[
            discord.IntegrationType.user_install,
            discord.IntegrationType.guild_install,
        ],
    )
    @cooldown(1, 10, BucketType.default)
    async def yuri(self, ctx: discord.ApplicationContext):
        try:
            with engine.begin() as c:
                yuri_filename, yuri_source = get_some_yuri(c)

            gallery = MediaGallery()
            gallery.add_item(f"attachment://{yuri_filename.split('/')[-1]}")

            container = Container()
            container.add_item(gallery)
            container.add_item(Separator())
            container.add_item(
                ActionRow(
                    Button(
                        label="more yuri :3",
                        style=ButtonStyle.primary,
                        custom_id="more_yuri_pwease_uwu",
                    ),
                    Button(
                        label="source",
                        style=ButtonStyle.link,
                        url=yuri_source,
                    ),
                )
            )

            await ctx.respond(
                view=DesignerView(container),
                file=File(yuri_filename),
            )
        except Exception as e:
            lunamon_logger.exception(
                "Error occured when posting yuri, the world is gonna end"
            )
            await ctx.respond(f"Error: {str(e)}", ephemeral=True)

    @discord.slash_command(
        name="targetlang",
        description="Set target language for translator",
        integration_types=[discord.IntegrationType.user_install],
    )
    async def set_target_language(self, ctx: discord.ApplicationContext, lang: str):
        if ctx.user.id != int(OWNER):
            await ctx.respond(
                "You are not authorized to use this command!", ephemeral=True
            )
            return

        if lang == "en":
            lang = Language.ENGLISH_AMERICAN

        self.target_language = lang
        await ctx.respond(f"targetlang = {lang}", ephemeral=True)

    @discord.message_command(
        name="Translate Message",
        description="Translate message to target language",
        integration_types=[discord.IntegrationType.user_install],
    )
    async def translate(
        self, ctx: discord.ApplicationContext, message: discord.Message
    ):
        try:
            if ctx.user.id != int(OWNER):
                await ctx.respond(
                    "You are not authorized to use this command!", ephemeral=True
                )
                return

            original = message.clean_content
            translated = deepl_client.translate_text(
                original, target_lang=self.target_language
            )

            await ctx.respond(
                f"Translated from {translated.detected_source_lang}:\n\n{translated.text}"
            )
        except Exception:
            lunamon_logger.exception("Error when translate message")
            await ctx.respond("An error occurred", ephemeral=True)

    @discord.slash_command(
        name="sotruebestie",
        description="So true bestie",
        integration_types=[discord.IntegrationType.user_install],
    )
    async def so_true_bestie(self, ctx: discord.ApplicationContext):
        try:
            await ctx.respond(file=discord.File("rom/sotruebestie.gif"))
        except Exception:
            lunamon_logger.exception(
                "Error when posting so true bestie, the world is gonna end"
            )

    @tasks.loop(seconds=5)
    async def handle_queue(self):
        try:
            if len(dm_cache) == 0:
                return

            message = "\n".join(dm_cache)

            owner = self.bot.get_user(int(OWNER))
            await owner.send(message)

            dm_cache.clear()
        except Exception:
            lunamon_logger.exception("Error occured when handling queue events")


def setup(bot: Bot):
    bot.add_cog(UserCommands(bot))
