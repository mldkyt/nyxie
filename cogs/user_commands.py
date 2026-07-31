import asyncio
import datetime
import os.path
import random
import shutil
import string
import subprocess
import sys

import aiohttp
import deepl
import discord
import pytz
from deepl import Language
from discord import (
    Bot,
    Embed,
    EmbedField,
    EmbedFooter,
    File,
    Interaction,
)
from discord.ext import commands, tasks
from discord.ext.commands import BucketType, cooldown
from discord.ui import (
    Button,
    View,
    button,
)
from sentry_sdk import capture_exception

from constants import (
    CHANNEL_MEMES,
    CHANNEL_MODERATION,
    DEEPL_API_KEY,
    GUILD,
    OWNER,
    VERSION,
)
from database import engine
from util.keysmash_generator import keysmash_ai
from util.storage import get_data, set_data
from util.yuri_util import get_some_yuri, get_some_yaoi

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
        except Exception as e:
            capture_exception(e)
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
        except Exception as e:
            capture_exception(e)
            await interaction.respond(
                "error :(\n-# this error was automatically reported", ephemeral=True
            )

class MoreYuriView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(
        label="more yuri!",
        style=discord.ButtonStyle.primary,
        custom_id="more_yuri_pwease_uwu",
    )
    async def more_yuri(self, button: Button, interaction: Interaction):
        with engine.begin() as c:
            yuri_filename, yuri_source = get_some_yuri(c)

        if not yuri_filename:
            await interaction.respond("No more yuri :(", ephemeral=True)
            return

        embed = Embed(
            title="Yuri :3",
            description=f"[source]({yuri_source})",
            image=f"attachment://{yuri_filename.split('/')[-1]}",
            footer=EmbedFooter(f"Lunamon {VERSION}"),
        )

        await interaction.respond(
            embed=embed, file=File(yuri_filename), view=MoreYuriView(), ephemeral=True
        )

class UserCommands(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.target_language = Language.ENGLISH_AMERICAN

    @discord.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(ReadReceiptComponent())
        self.bot.add_view(RefreshTimeView())
        self.bot.add_view(MoreYuriView())
        self.handle_queue.start()

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
        except Exception as e:
            capture_exception(e)

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
        except Exception as e:
            capture_exception(e)
            await ctx.respond(
                "An error occurred while executing the command.", ephemeral=True
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
        except Exception as e:
            capture_exception(e)
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
        except Exception as e:
            capture_exception(e)
            await ctx.respond(
                "An error occurred while executing the command.", ephemeral=True
            )

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
        except Exception as e:
            capture_exception(e)
            await ctx.respond("Error!", ephemeral=True)

    @discord.slash_command(name="version", description="Print bot version")
    async def version(self, ctx: discord.ApplicationContext):
        try:
            await ctx.respond(
                f"# Lunamon version {VERSION}\n\n"
                f"Python {sys.version} on {sys.platform}\n"
                f"py-cord {discord.__version__}\n"
                f"Licensed under GNU AGPL v3.0. Software's source code is [here](<https://git.mldkyt.com/mldkyt/mldmon>)",
                ephemeral=True,
            )
        except Exception as e:
            capture_exception(e)
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

            if not yuri_filename:
                await ctx.respond("No yuri found :(", ephemeral=True)
                return

            embed = Embed(
                title="Yuri :3",
                description=f"[source]({yuri_source})",
                image=f"attachment://{yuri_filename.split('/')[-1]}",
                footer=EmbedFooter(f"Lunamon {VERSION}"),
            )

            await ctx.respond(
                embed=embed, file=File(yuri_filename), view=MoreYuriView()
            )
        except Exception as e:
            await ctx.respond(f"Error: {str(e)}", ephemeral=True)

    @discord.slash_command(
        name="yaoi",
        description="boys,,,, men,,,,",
        integration_types=[
            discord.IntegrationType.user_install,
            discord.IntegrationType.guild_install,
        ],
    )
    @cooldown(1, 10, BucketType.default)
    async def yaol(self, ctx: discord.ApplicationContext):
        try:
            with engine.begin() as c:
                yaoi_filename, yaoi_source = get_some_yaoi(c)

            if not yaoi_filename:
                await ctx.respond("No yuri found :(", ephemeral=True)
                return

            embed = Embed(
                title="Yaoi :3",
                description=f"[source]({yaoi_source})",
                image=f"attachment://{yaoi_filename.split('/')[-1]}",
                footer=EmbedFooter(f"Lunamon {VERSION}"),
            )

            await ctx.respond(
                embed=embed, file=File(yaoi_filename), view=MoreYuriView()
            )
        except Exception as e:
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
        except Exception as e:
            capture_exception(e)
            await ctx.respond("An error occurred", ephemeral=True)

    @discord.slash_command(
        name="sotruebestie",
        description="So true bestie",
        integration_types=[discord.IntegrationType.user_install],
    )
    async def so_true_bestie(self, ctx: discord.ApplicationContext):
        try:
            await ctx.respond(file=discord.File("rom/sotruebestie.gif"))
        except Exception as e:
            capture_exception(e)

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
            capture_exception(e)


def setup(bot: Bot):
    bot.add_cog(UserCommands(bot))
