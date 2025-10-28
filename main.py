import logging
import os

import discord
from discord.ext import commands

from constants import DISCORD_TOKEN

ai_logger = logging.getLogger("ai")
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

ai_logger.setLevel(logging.DEBUG)

if not os.path.exists("logs"):
    os.mkdir("logs")

file_handler = logging.FileHandler(filename="logs/ai.log", mode="a", encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)

ai_logger.addHandler(file_handler)
ai_logger.addHandler(console_handler)

bot = discord.Bot(intents=discord.Intents.all())

for filename in os.listdir('cogs'):
    if filename.endswith('.py'):
        bot.load_extension(f'cogs.{filename[:-3]}')

@bot.event
async def on_ready():
    if not bot.user:
        return

    logging.info(f"{bot.user.display_name} has connected to Discord!")

@bot.event
async def on_application_command_error(ctx: discord.ApplicationContext, error):
    if isinstance(error, commands.CommandOnCooldown):
        minutes = int(error.retry_after / 60)
        seconds = int(error.retry_after % 60)
        if minutes > 0:
            await ctx.respond(
                f"Cooldown! {minutes} minutes and {seconds} seconds remaining :3",
                ephemeral=True)
        else:
            await ctx.respond(f"Cooldown! {seconds} seconds remaining :3", ephemeral=True)
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.respond(f"Missing permissions UwU!\nThese are missing: {', '.join(error.missing_permissions)}",
            ephemeral=True)
        return

    if isinstance(error, commands.NoPrivateMessage):
        await ctx.respond("This command was only meant for servers... :(", ephemeral=True)
        return

    if isinstance(error, commands.BotMissingPermissions):
        await ctx.respond(f"Sowwie Lunya gave too little permissions to me :( ask her to give me {', '.join(error.missing_permissions)} 🥺",
            ephemeral=True)
        return

    if isinstance(error, commands.PrivateMessageOnly):
        await ctx.respond("This command was only meant to be used in DM's with me 👉👈", ephemeral=True)
        return

    ai_logger.exception("An error occurred:")
    try:
        # respond
        await ctx.respond("An error occurred with this command, please ask Lunya to fix it :(", ephemeral=True)
    except Exception as e:
        pass
    raise error

bot.run(DISCORD_TOKEN)
