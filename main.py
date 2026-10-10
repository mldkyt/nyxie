import logging
import os

import discord
import sentry_sdk
from discord.ext import commands
from sentry_sdk import capture_exception
from sentry_sdk.integrations.logging import LoggingIntegration

from constants import DISCORD_TOKEN, SENTRY_SDK
from logger import nyxie_logger

bot = discord.Bot(intents=discord.Intents.all())

if SENTRY_SDK:
    sentry_sdk.init(
        dsn=SENTRY_SDK,
        integrations=[
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
        send_default_pii=True,
        max_request_body_size="always",
        traces_sample_rate=1,
        auto_session_tracking=False,
    )

for filename in os.listdir("cogs"):
    if filename.endswith(".py"):
        bot.load_extension(f"cogs.{filename[:-3]}")


@bot.event
async def on_ready():
    print("Ready as", bot.user.name)
    print("Gateway ping is", bot.latency * 1000, "ms")


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
            f"Sowwie mldkyt gave too little permissions to me :( ask her to give me {', '.join(error.missing_permissions)} 🥺",
            ephemeral=True,
        )
        return

    if isinstance(error, commands.PrivateMessageOnly):
        await ctx.respond(
            "This command was only meant to be used in DM's with me 👉👈",
            ephemeral=True,
        )
        return

    try:
        # respond
        await ctx.respond(
            "An error occurred with this command, please ask mldkyt to fix it :(",
            ephemeral=True,
        )
    except Exception:
        nyxie_logger.exception("Application command error")

    capture_exception(error)


bot.run(DISCORD_TOKEN)
