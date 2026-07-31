import os

import discord
import sentry_sdk
from discord.ext import commands
from sentry_sdk import capture_exception

from constants import DISCORD_TOKEN, SENTRY_SDK
from logger import lunamon_logger

bot = discord.Bot(intents=discord.Intents.all())

if SENTRY_SDK:
    sentry_sdk.init(
        SENTRY_SDK,
        send_default_pii=True,
        max_request_body_size="always",
        traces_sample_rate=0,
        send_client_reports=False,
        auto_session_tracking=False,
    )

for filename in os.listdir("cogs"):
    if filename.endswith(".py"):
        lunamon_logger.info(f"Loading {filename[:-3]}")
        bot.load_extension(f"cogs.{filename[:-3]}")


@bot.event
async def on_ready():
    if not bot.user:
        return

    lunamon_logger.info(f"{bot.user.display_name} has connected to Discord!")


@bot.event
async def on_application_command_error(ctx: discord.ApplicationContext, error):
    if isinstance(error, commands.CommandOnCooldown):
        minutes = int(error.retry_after / 60)
        seconds = int(error.retry_after % 60)
        if minutes > 0:
            await ctx.respond(
                f"Cooldown! {minutes} minutes and {seconds} seconds remaining :3",
                ephemeral=True,
            )
        else:
            await ctx.respond(
                f"Cooldown! {seconds} seconds remaining :3", ephemeral=True
            )
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.respond(
            f"Missing permissions UwU!\nThese are missing: {', '.join(error.missing_permissions)}",
            ephemeral=True,
        )
        return

    if isinstance(error, commands.NoPrivateMessage):
        await ctx.respond(
            "This command was only meant for servers... :(", ephemeral=True
        )
        return

    if isinstance(error, commands.BotMissingPermissions):
        await ctx.respond(
            f"Sowwie Lunya gave too little permissions to me :( ask her to give me {', '.join(error.missing_permissions)} 🥺",
            ephemeral=True,
        )
        return

    if isinstance(error, commands.PrivateMessageOnly):
        await ctx.respond(
            "This command was only meant to be used in DM's with me 👉👈",
            ephemeral=True,
        )
        return

    lunamon_logger.exception("An error occurred:")
    try:
        # respond
        await ctx.respond(
            "An error occurred with this command, please ask Lunya to fix it :(",
            ephemeral=True,
        )
    except Exception as e:
        capture_exception(e)

    capture_exception(error)


lunamon_logger.info("Starting Lunamon")
bot.run(DISCORD_TOKEN)
