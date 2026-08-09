import datetime
import random
import string
import subprocess
import sys

import discord
import pytz
from discord import (
    Bot,
    Embed,
    EmbedFooter,
    File,
    Interaction,
)
from discord.ext import tasks
from discord.ui import (
    Button,
    View,
    button,
)
from sentry_sdk import capture_exception

from constants import (
    OWNER,
    VERSION,
)
from database import engine
from util.yuri_util import get_some_yaoi, get_some_yuri

dm_cache = []


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


class MoreYuriView(View):
    def __init__(self, more_yuri_spam_btn: bool = False):
        super().__init__(timeout=None)

        self.more_yuri_spam_btn = more_yuri_spam_btn

    @button(
        label="more yuri!",
        style=discord.ButtonStyle.primary,
        custom_id="more_yuri_pwease_uwu",
    )
    async def more_yuri(self, button: Button, interaction: Interaction):
        with engine.begin() as c:
            yuri_filename, yuri_source, cw, alt = get_some_yuri(c)

        if not yuri_filename:
            await interaction.respond("No more yuri :(", ephemeral=True)
            return

        if not cw:
            cw = ""

        embed = Embed(
            title="Yuri :3",
            description=f"[source]({yuri_source})",
            image=f"attachment://{yuri_filename.split('/')[-1]}",
            footer=EmbedFooter(f"mldmon {VERSION}"),
        )

        await interaction.respond(
            embed=embed,
            file=File(yuri_filename, spoiler=len(cw.strip()) > 0, description=alt),
            view=MoreYuriView(more_yuri_spam_btn=self.more_yuri_spam_btn),
            ephemeral=not self.more_yuri_spam_btn,
        )


class MoreYaoiView(View):
    def __init__(self, more_yaoi_spam_btn: bool = False):
        super().__init__(timeout=None)

        self.more_yaoi_spam_btn = more_yaoi_spam_btn

    @button(
        label="more yaoi!",
        style=discord.ButtonStyle.primary,
        custom_id="more_yaoi_pwease_uwu",
    )
    async def more_yaoi(self, button: Button, interaction: Interaction):
        with engine.begin() as c:
            yaoi_filename, yaoi_source, cw, alt = get_some_yaoi(c)

        if not yaoi_filename:
            await interaction.respond("No more yaoi :(", ephemeral=True)
            return

        if not cw:
            cw = ""

        embed = Embed(
            title="Yaoi :3",
            description=f"[source]({yaoi_source})",
            image=f"attachment://{yaoi_filename.split('/')[-1]}",
            footer=EmbedFooter(f"mldmon {VERSION}"),
        )

        await interaction.respond(
            embed=embed,
            file=File(yaoi_filename, spoiler=len(cw.strip()) > 0, description=alt),
            view=MoreYaoiView(more_yaoi_spam_btn=self.more_yaoi_spam_btn),
            ephemeral=not self.more_yaoi_spam_btn,
        )


class UserCommands(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.Cog.listener()
    async def on_ready(self):
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
                f"# mldmon version {VERSION}\n"
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

    @discord.slash_command(name="version", description="Print bot version")
    async def version(self, ctx: discord.ApplicationContext):
        try:
            await ctx.respond(
                f"# mldmon version {VERSION}\n\n"
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
    async def yuri(
        self,
        ctx: discord.ApplicationContext,
        more_yuri_btn: bool = False,
        more_yuri_spam_btn: bool = False,
    ):
        try:
            with engine.begin() as c:
                yuri_filename, yuri_source, cw, alt = get_some_yuri(c)

            if not yuri_filename:
                await ctx.respond("No yuri found :(", ephemeral=True)
                return

            if not cw:
                cw = ""

            if len(cw.strip()) == 0:
                embed = Embed(
                    title="Yuri :3",
                    description=f"[source]({yuri_source})",
                    image=f"attachment://{yuri_filename.split('/')[-1]}",
                    footer=EmbedFooter(f"mldmon {VERSION}"),
                )
            else:
                embed = Embed(
                    title="Yuri :3",
                    description=f"[source]({yuri_source})",
                    footer=EmbedFooter(f"mldmon {VERSION}"),
                )

            await ctx.respond(
                embed=embed,
                file=File(yuri_filename, spoiler=len(cw.strip()) > 0, description=alt),
                view=MoreYuriView(more_yuri_spam_btn=more_yuri_spam_btn)
                if more_yuri_btn
                else None,
            )
        except Exception as e:
            capture_exception(e)
            await ctx.respond(f"Error: {e!s}", ephemeral=True)

    @discord.slash_command(
        name="yaoi",
        description="boys,,,, men,,,,",
        integration_types=[
            discord.IntegrationType.user_install,
            discord.IntegrationType.guild_install,
        ],
    )
    async def yaol(
        self,
        ctx: discord.ApplicationContext,
        more_yaol_btn: bool = False,
        more_yaol_spam_btn: bool = False,
    ):
        try:
            with engine.begin() as c:
                yaoi_filename, yaoi_source, cw, alt = get_some_yaoi(c)

            if not yaoi_filename:
                await ctx.respond("No yuri found :(", ephemeral=True)
                return

            if not cw:
                cw = ""

            if len(cw.strip()) == 0:
                embed = Embed(
                    title="Yaoi :3",
                    description=f"[source]({yaoi_source})",
                    image=f"attachment://{yaoi_filename.split('/')[-1]}",
                    footer=EmbedFooter(f"mldmon {VERSION}"),
                )
            else:
                embed = Embed(
                    title="Yaoi :3",
                    description=f"[source]({yaoi_source})",
                    footer=EmbedFooter(f"mldmon {VERSION}"),
                )

            await ctx.respond(
                embed=embed,
                file=File(yaoi_filename, spoiler=len(cw.strip()) > 0, description=alt),
                view=MoreYaoiView(more_yaoi_spam_btn=more_yaol_spam_btn)
                if more_yaol_btn
                else None,
            )
        except Exception as e:
            capture_exception(e)
            await ctx.respond(f"Error: {e!s}", ephemeral=True)

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
