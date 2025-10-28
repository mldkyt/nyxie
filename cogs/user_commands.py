import asyncio
import datetime
import logging
import os.path
import random
import shutil
import string
import subprocess
import sys

import aiohttp
import discord
import libretranslatepy
import pytz
import requests
import yt_dlp.version
from bs4 import BeautifulSoup
from discord import Interaction, Bot
from discord.ext import tasks, commands
from discord.ext.commands import cooldown, BucketType
from mastodon import Mastodon

from constants import OWNER, FEDI_INSTANCE, GUILD, CHANNEL_MODERATION, CHANNEL_MEMES, VERSION, \
    FORGEJO_INSTANCE, FORGEJO_DEFAULT_USER, FORGEJO_TOKEN, LIBRETRANSLATE_URL, LIBRETRANSLATE_API_KEY
from util.keysmash_generator import keysmash_ai
from util.storage import get_data, set_data

dm_cache = []

ai_logger = logging.getLogger("ai")

libretranslate = libretranslatepy.LibreTranslateAPI(LIBRETRANSLATE_URL, LIBRETRANSLATE_API_KEY)

mastodon = Mastodon(access_token='data/usercred', api_base_url=f'https://{FEDI_INSTANCE}')

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
        return "".join(random.choices(string.ascii_lowercase, k=random.randint(3, 25))) + " >" + "/" * random.randint(3,
                                                                                                                      10) + "<"
    else:
        raise ValueError("Invalid fluster type")

class RefreshTimeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="refresh", style=discord.ButtonStyle.secondary, custom_id="refresh_time")
    async def refresh_btn(self, button: discord.ui.Button, interaction: discord.Interaction):
        try:
            utc = pytz.timezone("UTC")
            lunya_tz = pytz.timezone("Europe/Prague")

            utc_time = datetime.datetime.now(utc)
            lunya_time = datetime.datetime.now(lunya_tz)

            await interaction.edit(content=f"# Time\n"
                                           f"Current time for Lunya: {lunya_time.strftime('%a %d %b %Y, %H:%M:%S %Z (%z)')}\n"
                                           f"Server clock: {utc_time.strftime('%a %d %b %Y, %H:%M:%S %Z (%z)')}\n"
                                           f"Your time: <t:{int(utc_time.timestamp())}:F>")
        except Exception as e:
            ai_logger.exception("An error occurred:")
            await interaction.response.send_message(f"error :(", ephemeral=True)

class ReadReceiptComponent(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Mark as read", style=discord.ButtonStyle.primary, custom_id="read_receipt")
    async def mark_as_read(self, button: discord.ui.Button, interaction: discord.Interaction):
        try:
            data = get_data(f"read_receipt/{interaction.message.id}")

            if 'readUsers' not in data:
                data['readUsers'] = []

            if 'message' not in data:
                data['message'] = interaction.message.content

            if str(interaction.user.id) in data['readUsers']:
                await interaction.respond("already marked as read! thank you <3", ephemeral=True)
                return

            data['readUsers'].append(str(interaction.user.id))

            await interaction.edit(content=f'{data["message"]}\n*Read by {", ".join([f"<@{i}>" for i in data["readUsers"]])}*')
            set_data(f"read_receipt/{interaction.message.id}", data)
        except Exception as e:
            ai_logger.exception("An error occurred:")
            await interaction.respond("error :(\n"
                                      "-# this error was automatically reported", ephemeral=True)



class PickerComponent(discord.ui.View):
    def __init__(self, type: str):
        super().__init__(timeout=None)

        if type == "meow":
            meow_btn = discord.ui.Button(style=discord.ButtonStyle.primary, label="Meow", custom_id="picker_meow")
            meow_btn.callback = self.meow
            self.add_item(meow_btn)
        elif type == ":3":
            colon_three_button = discord.ui.Button(style=discord.ButtonStyle.primary, label=":3",
                                                   custom_id="picker_colon_three")
            colon_three_button.callback = self.colon_three
            self.add_item(colon_three_button)
        elif type == "compliments":
            # cute
            cute_button = discord.ui.Button(style=discord.ButtonStyle.primary, label="such a cute girl~ :3",
                                            custom_id="picker_cute")
            cute_button.callback = self.cute
            self.add_item(cute_button)

            # pretty
            pretty_button = discord.ui.Button(style=discord.ButtonStyle.primary, label="such a pretty girl~ :3",
                                              custom_id="picker_pretty")
            pretty_button.callback = self.pretty
            self.add_item(pretty_button)

            # gorgeous

            gorgeous_button = discord.ui.Button(style=discord.ButtonStyle.primary, label="such a gorgeous girl :3",
                                                custom_id="picker_gorgeous")
            gorgeous_button.callback = self.gorgeous
            self.add_item(gorgeous_button)

            # cool

            cool_button = discord.ui.Button(style=discord.ButtonStyle.primary, label="such a cool girl~ :3",
                                            custom_id="picker_cool")
            cool_button.callback = self.cool
            self.add_item(cool_button)

            # good girl

            good_girl_button = discord.ui.Button(style=discord.ButtonStyle.primary, label="such a goooood girl~ :3",
                                                 custom_id="picker_good_girl")
            good_girl_button.callback = self.good_girl
            self.add_item(good_girl_button)
        elif type == "meowat":
            meow_at_button = discord.ui.Button(style=discord.ButtonStyle.primary, label="meow at Lunya :3",
                                               custom_id="picker_meow_at")
            meow_at_button.callback = self.meowat
            self.add_item(meow_at_button)
        elif type == "purrr":
            purrr_button = discord.ui.Button(style=discord.ButtonStyle.primary, label="purrr :3",
                                             custom_id="picker_purrr")
            purrr_button.callback = self.purrr
            self.add_item(purrr_button)
        elif type == "girlkiss":
            girlkiss_button = discord.ui.Button(style=discord.ButtonStyle.primary,
                                                label="girlkiss a girl Lunya :3 (real) UwU",
                                                custom_id="picker_girlkiss")
            girlkiss_button.callback = self.girlkiss
            self.add_item(girlkiss_button)
        elif type == "boop":
            boop_button = discord.ui.Button(style=discord.ButtonStyle.primary, label="boop :3", custom_id="picker_boop")
            boop_button.callback = self.boop
            self.add_item(boop_button)
        elif type == "paws":
            paws_at_you_button = discord.ui.Button(style=discord.ButtonStyle.primary, label="*paws at you*",
                                                   custom_id="picker_paws")
            paws_at_you_button.callback = self.paws_at_you
            self.add_item(paws_at_you_button)
        elif type == "click":
            self.click_button = discord.ui.Button(style=discord.ButtonStyle.primary, label="*click click*",
                                             custom_id="picker_click")
            self.click_button.callback = self.click
            self.add_item(self.click_button)
        elif type == "beep":
            self.click_button = discord.ui.Button(style=discord.ButtonStyle.primary, label="beeeeep",
                                                  custom_id="picker_beep")
            self.click_button.callback = self.beep
            self.add_item(self.click_button)
        else:
            raise ValueError("Invalid type")

    async def meow(self, interaction: discord.Interaction):
        try:
            meow = generate_meow()
            await interaction.respond(f"✅ Message sent\n{meow} :3", ephemeral=True)
            dm_cache.append(f"{meow} by {interaction.user.mention} :3")
        except Exception as e:
            ai_logger.exception("An error occurred:")
            await interaction.respond("An error occurred", ephemeral=True)

    async def colon_three(self, interaction: discord.Interaction):
        try:
            colon_three = ':' + '3' * random.randint(4, 12)
            await interaction.respond(f"✅ Message sent\n:{colon_three} :3", ephemeral=True)
            dm_cache.append(f"{colon_three} by {interaction.user.mention} :3")
        except Exception as e:
            ai_logger.exception("An error occurred:")
            await interaction.respond("An error occurred", ephemeral=True)

    async def cute(self, interaction: discord.Interaction):
        try:
            await interaction.respond(f"✅ {generate_fluster()}", ephemeral=True)
            dm_cache.append(f"{interaction.user.mention} said that you're such a cute girl~ :3")
        except Exception as e:
            ai_logger.exception("An error occurred:")
            await interaction.respond("An error occurred", ephemeral=True)

    async def pretty(self, interaction: discord.Interaction):
        try:
            await interaction.respond(f"✅ {generate_fluster()}", ephemeral=True)
            dm_cache.append(f"{interaction.user.mention} said that you're such a pretty girl~ :3")
        except Exception as e:
            ai_logger.exception("An error occurred:")
            await interaction.respond("An error occurred", ephemeral=True)

    async def gorgeous(self, interaction: discord.Interaction):
        try:
            await interaction.respond(f"✅ {generate_fluster()}", ephemeral=True)
            dm_cache.append(f"{interaction.user.mention} said that you're such a gorgeous girl~ :3")
        except Exception as e:
            ai_logger.exception("An error occurred:")
            await interaction.respond("An error occurred", ephemeral=True)

    async def cool(self, interaction: discord.Interaction):
        try:
            await interaction.respond(f"✅ {generate_fluster()}", ephemeral=True)
            dm_cache.append(f"{interaction.user.mention} said that you're such a coool girl~ :3")
        except Exception as e:
            ai_logger.exception("An error occurred:")
            await interaction.respond("An error occurred", ephemeral=True)

    async def good_girl(self, interaction: discord.Interaction):
        try:
            await interaction.respond(f"✅ {generate_fluster()} {generate_fluster()}", ephemeral=True)
            dm_cache.append(f"{interaction.user.mention} said that you're such a goooood girl~ :3")
        except Exception as e:
            ai_logger.exception("An error occurred:")
            await interaction.respond("An error occurred", ephemeral=True)

    async def meowat(self, interaction: discord.Interaction):
        try:
            await interaction.respond(f"✅ meow -> <@{OWNER}>", ephemeral=True)
            dm_cache.append(f"{interaction.user.mention} meowd at you :3")
        except Exception as e:
            ai_logger.exception("An error occurred:")
            await interaction.respond("An error occurred", ephemeral=True)

    async def purrr(self, interaction: discord.Interaction):
        try:
            await interaction.respond("✅ *purrrrrrr*", ephemeral=True)
            dm_cache.append(f"{interaction.user.mention} has *purrrrr* :3")
        except Exception as e:
            ai_logger.exception("An error occurred:")
            await interaction.respond("An error occurred", ephemeral=True)

    async def girlkiss(self, interaction: discord.Interaction):
        try:
            await interaction.respond("✅ Girls were kissed :3", ephemeral=True)
            dm_cache.append(f"{interaction.user.mention} has give you girlkiss :3333333333")
        except Exception as e:
            ai_logger.exception("An error occurred:")
            await interaction.respond("An error occurred", ephemeral=True)

    async def boop(self, interaction: discord.Interaction):
        try:
            await interaction.respond("✅ >///<", ephemeral=True)
            dm_cache.append(f"{interaction.user.mention} has booped you :3")
        except Exception as e:
            ai_logger.exception("An error occurred:")
            await interaction.respond("An error occurred", ephemeral=True)

    async def paws_at_you(self, interaction: discord.Interaction):
        try:
            await interaction.respond("✅ *paws at Lunya*", ephemeral=True)
            dm_cache.append(f"{interaction.user.mention} *paws at you* :3")
        except Exception as e:
            ai_logger.exception("An error occurred:")
            await interaction.respond("An error occurred", ephemeral=True)

    async def beep(self, interaction: discord.Interaction):
        try:
            await interaction.respond("✅ beeeeep", ephemeral=True)
            dm_cache.append(f"{interaction.user.mention} beeped at you :3")
        except Exception as e:
            ai_logger.exception("An error occurred:")
            await interaction.respond("An error occurred", ephemeral=True)

    async def click(self, interaction: discord.Interaction):
        try:
            await interaction.respond("✅ *click click* at Lunya", ephemeral=True)

            click_data = get_data("clicker")
            # total
            if 'total' not in click_data:
                click_data['total'] = 0

            click_data['total'] += 1

            # per user
            if 'from' not in click_data:
                click_data['from'] = {}

            if str(interaction.user.id) not in click_data['from']:
                click_data['from'][str(interaction.user.id)] = 0

            click_data['from'][str(interaction.user.id)] += 1

            set_data("clicker", click_data)

            dm_cache.append(f"{interaction.user.mention} clicked at you :3")
        except Exception as e:
            ai_logger.exception("An error occurred:")
            await interaction.respond("An error occurred", ephemeral=True)


class ForgejoCreateIssueModal(discord.ui.Modal):
    def __init__(self, user: str, repo: str):
        super().__init__(title=f"create issue on {user}/{repo}")

        self.user = user
        self.repo = repo

        self.field_title = discord.ui.InputText(label="title", placeholder="[feat] meow uwu :3")
        self.add_item(self.field_title)

        self.field_body = discord.ui.InputText(label="body", placeholder="- [ ] add meowing\n"
                                                                         "- [ ] add woofing...", style=discord.InputTextStyle.paragraph)
        self.add_item(self.field_body)

    async def callback(self, interaction: Interaction):
        try:
            if interaction.user is None:
                await interaction.respond("user is null for some godforsaken reason", ephemeral=True)
                return

            res = requests.post(f"https://{FORGEJO_INSTANCE}/api/v1/repos/{self.user}/{self.repo}/issues", headers={
                'Authorization': f"Bearer {FORGEJO_TOKEN}",
                'Content-Type': 'application/json'
            }, json={
                'title': self.field_title.value,
                'body': f'User {interaction.user.display_name} ({interaction.user.name}, {interaction.user.id}) submitted the following:\n\n{self.field_body.value}'
            })

            res.raise_for_status()
            res_b = res.json()

            await interaction.respond("Issue created successfully!\n"
                                      f"https://{FORGEJO_INSTANCE}/{self.user}/{self.repo}/issues/{res_b['number']}", ephemeral=True)
        except Exception as e:
            ai_logger.exception("An error occurred:")
            await interaction.respond("an error occurred", ephemeral=True)

class ForgejoCreateIssueButton(discord.ui.View):
    def __init__(self, user: str, repo: str):
        super().__init__(timeout=3600, disable_on_timeout=True)
        self.user = user
        self.repo = repo

    @discord.ui.button(label="create issue", style=discord.ButtonStyle.primary)
    async def create_issue_modal(self, button: discord.ui.Button, interaction: discord.Interaction):
        try:
            await interaction.response.send_modal(ForgejoCreateIssueModal(user=self.user, repo=self.repo))
        except Exception as e:
            ai_logger.exception("An error occurred:")
            await interaction.respond("an error occurred", ephemeral=True)


async def uwuify(text: str) -> str | None:
    # Send request
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=1)) as session:
        async with session.post("https://uwu.pm/api/v1/uwu", json={
            "text": text,
            "provider": "uwwwupp"
        }) as res:

            if res.status != 200:
                return None

            res = await res.json()

            if "uwu" not in res or res["uwu"] is None:
                return None

            return res["uwu"]


class MoreYuriView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="more", style=discord.ButtonStyle.primary, custom_id="more_yuri_pwease_uwu")
    async def more_yuri(self, button: discord.ui.Button, interaction: discord.Interaction):
        try:
            items = os.listdir("data/yuri")
            item = random.choice(items)

            index = items.index(item)

            await interaction.respond(f"yuri!\nfile {index}/{len(items)} [/~lunya/girls,,,,/{item}](https://f.lunya.pet/~lunya/girls%252C%252C%252C/{item[:-4]}jpg) [(browse)](https://f.lunya.pet/~lunya/girls%252C%252C%252C/)",
                view=MoreYuriView())
        except Exception as e:
            await interaction.respond(f"Error: {str(e)}", ephemeral=True)
            ai_logger.exception("An error occured:")


class UserCommands(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.target_language = "en"

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
        self.bot.add_view(MoreYuriView())
        self.handle_queue.start()

    user_commands = discord.SlashCommandGroup(name='user', description='User commands',
                                              integration_types=[discord.IntegrationType.user_install])

    @user_commands.command(name='ping', description='Tests connection to Discord',
                           integration_types=[discord.IntegrationType.user_install])
    async def ping(self, ctx: discord.ApplicationContext):
        await ctx.respond(f'Pong! {self.bot.latency * 1500} ms', ephemeral=(ctx.user.id != int(OWNER)))

    @user_commands.command(name='message', description='Send message as bot',
                           integration_types=[discord.IntegrationType.user_install])
    async def message(self, ctx: discord.ApplicationContext, msg: str):
        if ctx.user.id != int(OWNER):
            await ctx.respond("You are not authorized to use this command!", ephemeral=True)
            return

        await ctx.respond(msg)

    @user_commands.command(name="information", description="Print information about the server",
                           integration_types=[discord.IntegrationType.user_install])
    async def information(self, ctx: discord.ApplicationContext, public: bool = False):
        try:
            if ctx.user.id != int(OWNER):
                await ctx.respond("You are not authorized to use this command!", ephemeral=True)
                return

            uname = subprocess.run(["uname", "-snrvmpio"], capture_output=True, text=True)
            uptime = subprocess.run(["uptime"], capture_output=True, text=True)
            version = (f"Python {sys.version} on {sys.platform}\n"
                      f"py-cord {discord.__version__}\n"
                      f"yt_dlp {yt_dlp.version.__version__} {yt_dlp.version.CHANNEL}\n")

            await ctx.respond(f"# 愛OS (AiOS) version {VERSION}\n"
                              f"```\n"
                              f"{uname.stdout.strip()}\n"
                              f"{uptime.stdout.strip()}\n"
                              f"{version}"
                              f"```",
                              ephemeral=not public)
        except Exception as e:
            ai_logger.exception("An error occurred:")
            await ctx.respond("An error occurred while executing the command.", ephemeral=True)

    @user_commands.command(name="picker")
    async def picker(self, ctx: discord.ApplicationContext,
                     message: str,
                     type: discord.Option(str,
                                          choices=["meow", "fedi meow", ":3", "fedi :3", "compliments", "meowat", "purrr", "girlkiss", "boop",
                                                   "paws", "click", "beep"])):
        try:
            if ctx.user.id != int(OWNER):
                await ctx.respond("You are not authorized to use this command!", ephemeral=True)
                return

            await ctx.respond(message, view=PickerComponent(type))
        except Exception as e:
            ai_logger.exception("An error occurred:")
            await ctx.respond("An error occurred while executing the command.", ephemeral=True)

    @user_commands.command(name="clicker_counts", description="how many times did i click at you?")
    async def clicker_counts(self, ctx: discord.ApplicationContext, from_user: discord.User = None, public: bool = False):
        try:
            if ctx.user.id != int(OWNER):
                await ctx.respond("You are not authorized to use this command!", ephemeral=True)
                return

            click_data = get_data("clicker")

            if 'total' not in click_data:
                click_data['total'] = 0
            if 'from' not in click_data:
                click_data['from'] = {}

            if from_user is None:
                await ctx.respond(f"a total of {click_data['total']} clicks has been done at you :3", ephemeral=not public)
                return

            if str(from_user.id) in click_data['from']:
                await ctx.respond(f"a total of {click_data['total']} clicks and {click_data['from'][str(from_user.id)]} clicks specifically from {from_user.mention} have been performed at you :3", ephemeral=not public)
            else:
                await ctx.respond(f"a total of {click_data['total']} clicks has been done at you :3\n"
                                  f"-# from user not found in db", ephemeral=not public)
        except Exception as e:
            ai_logger.exception("An error occurred:")
            await ctx.respond("an error occurred while executing the command.", ephemeral=True)

    @user_commands.command(name="read_receipt", description="Send read receipt message which allows well accepting a read receipt")
    async def read_receipt(self, ctx: discord.ApplicationContext, message: str):
        try:
            if ctx.user.id != int(OWNER):
                await ctx.respond("You are not authorized to use this command!", ephemeral=True)
                return

            await ctx.respond(message, view=ReadReceiptComponent())
        except Exception as e:
            ai_logger.exception("An error occurred:")
            await ctx.respond("An error occurred while executing the command.", ephemeral=True)

    @user_commands.command(name="time", description="Get time for Lunya :3")
    async def time(self, ctx: discord.ApplicationContext):
        try:
            if ctx.user.id != int(OWNER):
                await ctx.respond("You are not authorized to use this command!", ephemeral=True)
                return

            utc = pytz.timezone("UTC")
            lunya_tz = pytz.timezone("Europe/Prague")

            utc_time = datetime.datetime.now(utc)
            lunya_time = datetime.datetime.now(lunya_tz)

            await ctx.respond(f"# Time\n"
                              f"Current time for Lunya: {lunya_time.strftime('%a %d %b %Y, %H:%M:%S %Z (%z)')}\n"
                              f"Server clock: {utc_time.strftime('%a %d %b %Y, %H:%M:%S %Z (%z)')}\n"
                              f"Your time: <t:{int(utc_time.timestamp())}:F>", view=RefreshTimeView())
        except Exception as e:
            ai_logger.exception("An error occurred:")
            await ctx.respond("An error occurred while executing the command.", ephemeral=True)

    fedi_group = discord.SlashCommandGroup(name="fedi", description="Fedi commands",
                                           integration_types=[discord.IntegrationType.user_install])

    @fedi_group.command(name="search", description="Search on fedi",
                        integration_types=[discord.IntegrationType.user_install])
    @discord.option(name="media_only")
    @discord.option(name="content_type", choices=["posts", "users"])
    @discord.option(name="count", min=1, max=10)
    async def search(self, ctx: discord.ApplicationContext, q: str, content_type: str = 'posts',
                     media_only: bool = False, count: int = 3):
        try:
            # Verify right user
            if ctx.user.id != int(OWNER):
                await ctx.respond("You are not authorized to use this command!", ephemeral=True)
                return

            await ctx.defer()

            search = mastodon.search_v2(q, result_type="accounts" if content_type == "users" else "statuses")

            if content_type == 'users':
                text = f"# Users for term '{q}':\n"

                accounts = search.accounts
                accounts = [i for i in accounts if
                            '#nobot' not in i.note.lower() and
                            '#noindex' not in i.note.lower() and
                            '#noarchive' not in i.note.lower()]
                accounts = [i for i in accounts if not i.noindex]
                for i in range(len(accounts)):
                    if i >= count:
                        break

                    v = accounts[i]

                    text += f"{i + 1}. [{v.acct}](<https://{FEDI_INSTANCE}/{v.acct}>)\n"

                await ctx.followup.send(text)
            elif content_type == 'posts':
                text = f"# Posts for term '{q}'\n"

                statuses = search.statuses
                statuses = [i for i in statuses if i.visibility == 'public']
                statuses = [i for i in statuses if
                            '#nobot' not in i.account.note.lower() and
                            '#noindex' not in i.account.note.lower() and
                            '#noarchive' not in i.account.note.lower()]
                statuses = [i for i in statuses if not i.account.noindex]
                statuses = [i for i in statuses if len(i.media_attachments) > 0 or not media_only]

                for i in range(len(statuses)):
                    if i >= count:
                        break

                    v = statuses[i]

                    text += (f"{i + 1}. Post by "
                             f"[{v.account.acct}](https://{FEDI_INSTANCE}/{v.account.acct}): "
                             f"https://{FEDI_INSTANCE}/notice/{v.id}\n")

                await ctx.followup.send(text)
        except Exception as e:
            ai_logger.exception("An error occurred:")
            await ctx.followup.send(f"Error! Server error: {e=}")

    @fedi_group.command(name="post", description="Create a post on fedi",
                        integration_types=[discord.IntegrationType.user_install])
    @discord.option(name="visibility", choices=["public", "unlisted", "private"])
    async def post(self, ctx: discord.ApplicationContext, text: str, cw: str = "", visibility: str = "public",
                   public_response: bool = False):
        try:
            post = mastodon.status_post(text, spoiler_text=cw, visibility=visibility)
            await ctx.respond(post.url, ephemeral=not public_response)
        except Exception as e:
            ai_logger.exception("An error occurred:")
            await ctx.respond("Failed to create post!", ephemeral=True)

    forgejo_commands = discord.SlashCommandGroup(name="forgejo", description=f"Forgejo ({FORGEJO_INSTANCE}) related commands",
                                           integration_types=[discord.IntegrationType.user_install])

    @forgejo_commands.command(name="new_issue", description="Create an issue on a project", integration_types=[discord.IntegrationType.user_install])
    async def forgejo_new_issue(self, ctx: discord.ApplicationContext, project: str, title: str, body: str, user: str = FORGEJO_DEFAULT_USER):
        try:
            if ctx.user.id != int(OWNER):
                await ctx.respond("You are not authorized to use this command!", ephemeral=True)

            res = requests.post(f"https://{FORGEJO_INSTANCE}/api/v1/repos/{user}/{project}/issues", headers={
                'Authorization': f"Bearer {FORGEJO_TOKEN}",
                'Content-Type': 'application/json'
            }, json={
                'title': title,
                'body': body
            })

            res.raise_for_status()
            res_b = res.json()

            await ctx.respond("Issue created successfully!\n"
                              f"https://{FORGEJO_INSTANCE}/{user}/{project}/issues/{res_b['number']}", ephemeral=True)
        except Exception as e:
            ai_logger.exception("An error occurred:")
            await ctx.respond("Failed to create new issue!", ephemeral=True)

    @forgejo_commands.command(name="new_issue_button", description="Send a button allow submitting of issues to repository", integration_types=[discord.IntegrationType.user_install])
    async def forgejo_new_issue(self, ctx: discord.ApplicationContext, project: str, message: str, user: str = FORGEJO_DEFAULT_USER):
        try:
            if ctx.user.id != int(OWNER):
                await ctx.respond("You are not authorized to use this command!", ephemeral=True)

            await ctx.respond(message, view=ForgejoCreateIssueButton(user, project))
        except Exception as e:
            ai_logger.exception("An error occurred:")
            await ctx.respond("Failed to create new issue!", ephemeral=True)

    @user_commands.command(name='ban_from_lunya', description='Ban user from Lunya\'s Discord server',
                           integration_types=[discord.IntegrationType.user_install])
    async def ban_from_lunya(self, ctx: discord.ApplicationContext, user: discord.User, reason: str):
        try:
            # Verify right user
            if ctx.user.id != int(OWNER):
                await ctx.respond("You are not authorized to use this command!", ephemeral=True)
                return

            # Get guild

            guild = self.bot.get_guild(int(GUILD))

            # Ban user

            a = guild.ban(user, reason=reason, delete_message_seconds=7 * 24 * 3600)

            # Log message

            logs_channel = guild.get_channel(int(CHANNEL_MODERATION))

            b = logs_channel.send(embed=discord.Embed(
                title="Member Banned Externally",
                description=f"The member {user.mention} was banned here because Lunya issued a ban command from a different server.",
                fields=[
                    discord.EmbedField(name="Banned Member", value=user.mention, inline=True),
                    discord.EmbedField(name="Reason", value=reason, inline=True)
                ]
            ))

            c = ctx.respond("Member was banned successfully!", ephemeral=True)

            await asyncio.gather(a, b, c)
        except Exception as e:
            ai_logger.exception("An error occurred:")
            await ctx.respond("An error occured banning this user.", ephemeral=True)

    @user_commands.command(name="uwwwu", description="UwUify text",
                           integration_types=[discord.IntegrationType.user_install])
    async def uwuify_text(self, ctx: discord.ApplicationContext, text: str, private: bool = True):
        try:
            # Verify right user
            if ctx.user.id != int(OWNER):
                await ctx.respond("You are not authorized to use this command!", ephemeral=True)
                return

            # Send request
            uwuified = await uwuify(text)
            if uwuified is None:
                await ctx.respond("An error occured!", ephemeral=True)
                return

            await ctx.respond(uwuified, ephemeral=not private)
        except Exception as e:
            await ctx.respond(f"An error occured! {e=}", ephemeral=True)
            ai_logger.exception("An error occurred:")

    @discord.slash_command(name="uwuify", description="UwUify text")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def uwuify_text_public(self, ctx: discord.ApplicationContext, text: str, use_ai: discord.Option(bool,
                                                                                                          description="Do you want to use the latest cutting-edge AI to uwuify?",
                                                                                                          default=True)):
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
            await ctx.respond(f"An error occured! {e=}", ephemeral=True)
            ai_logger.exception("An error occurred:")

    @discord.message_command(name='Borrow Meme',
                             description='Repost the message inside of the memes channel of Lunya\'s Discord server',
                             integration_types=[discord.IntegrationType.user_install])
    async def borrow_meme(self, ctx: discord.ApplicationContext, message: discord.Message):
        try:
            if ctx.user.id != int(OWNER):
                await ctx.respond("You are not authorized to use this command!", ephemeral=True)
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
            await memes.send(content=message.content,
                             files=[discord.File(f"temp/{i.filename}", i.filename) for i in message.attachments])

            # Delete
            shutil.rmtree("temp")
        except Exception as e:
            await ctx.respond("Error!", ephemeral=True)
            ai_logger.exception("An error occurred:")

    @discord.slash_command(name="version", description="Print bot version")
    async def version(self, ctx: discord.ApplicationContext):
        try:
            await ctx.respond(f"# Ai version {VERSION}\n\n"
                              f"Python {sys.version} on {sys.platform}\n"
                              f"py-cord {discord.__version__}\n"
                              f"yt_dlp {yt_dlp.version.__version__} {yt_dlp.version.CHANNEL}\n\n"
                              f"Licensed under GNU AGPL v3.0. Software's source code is [here](<https://git.lunya.pet/Lunya/Ai>)", ephemeral=True)
        except Exception as e:
            await ctx.respond("Error!", ephemeral=True)
            ai_logger.exception("An error occurred:")

    @discord.slash_command(name="yuri", description="girls,,,, womeb,,,,", integration_types=[discord.IntegrationType.user_install, discord.IntegrationType.guild_install])
    @cooldown(1, 10, BucketType.default)
    async def yuri(self, ctx: discord.ApplicationContext):
        try:
            items = os.listdir("data/yuri")
            item = random.choice(items)
            print(item)

            index = items.index(item)

            await ctx.respond(f"yuri!\nfile {index}/{len(items)} [/~lunya/girls,,,/{item}](https://f.lunya.pet/~lunya/girls,,,/{item[:-4]}jpg) [(browse)](https://f.lunya.pet/~lunya/girls,,,/)",
                view=MoreYuriView())
        except Exception as e:
            await ctx.respond(f"Error: {str(e)}", ephemeral=True)
            ai_logger.exception("An error occured:")

    @discord.slash_command(name="targetlang", description="Set target language for translator", integration_types=[discord.IntegrationType.user_install])
    async def set_target_language(self, ctx: discord.ApplicationContext, lang: str):
        if ctx.user.id != int(OWNER):
            await ctx.respond("You are not authorized to use this command!", ephemeral=True)
            return

        self.target_language = lang
        await ctx.respond(f"targetlang = {lang}", ephemeral=True)

    @discord.message_command(name="Translate Message", description="Translate message to target language", integration_types=[discord.IntegrationType.user_install])
    async def translate(self, ctx: discord.ApplicationContext, message: discord.Message):
        try:
            if ctx.user.id != int(OWNER):
                await ctx.respond("You are not authorized to use this command!", ephemeral=True)
                return

            await ctx.defer()

            original = message.clean_content
            source_lang = libretranslate.detect(original)
            if len(source_lang) == 0:
                await ctx.respond("Language not detected successfully")
                return

            translated = libretranslate.translate(original, source_lang[0]['language'], self.target_language)

            await ctx.respond(f"{translated}\n\n-# Powered by LibreTranslate (language={source_lang[0]['language']};confidence={source_lang[0]['confidence']})")
        except Exception as e:
            await ctx.respond("An error occurred")
            ai_logger.exception("An error occured:")

    @discord.slash_command(name="sotruebestie", description="So true bestie", integration_types=[discord.IntegrationType.user_install])
    async def so_true_bestie(self, ctx: discord.ApplicationContext):
        await ctx.respond(file=discord.File("rom/sotruebestie.gif"))

    @tasks.loop(seconds=5)
    async def handle_queue(self):
        try:
            if len(dm_cache) == 0:
                return

            message = "\n".join(dm_cache)

            owner = self.bot.get_user(int(OWNER))
            await owner.send(message)

            dm_cache.clear()
        except Exception as e:
            ai_logger.exception("An error occurred:")

def setup(bot: Bot):
    bot.add_cog(UserCommands(bot))
