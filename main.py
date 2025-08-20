import logging
import os

import discord
from discord.ext import commands

from cogs.auto_fedi_notifs import AutoFediNotifications
from cogs.auto_yt_notifs import AutoYouTubeNotifications
from cogs.dev_commands import DevCommands
from cogs.funny_auto_response import FunnyAutoResponse
from cogs.general_cleaner import GeneralCleaner
from cogs.init_cache import InitCache
from cogs.media_threads import MediaThreads
from cogs.message_reporting import MessageReporting
from cogs.nsfw_verification import NsfwVerification
from cogs.user_commands import UserCommands
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
        await ctx.respond("An error occured with this command, please ask Lunya to fix it :(", ephemeral=True)
    except Exception as e:
        pass
    raise error

bot.add_cog(DevCommands(bot))
bot.add_cog(UserCommands(bot))
bot.add_cog(AutoFediNotifications(bot))
bot.add_cog(AutoYouTubeNotifications(bot))
bot.add_cog(MessageReporting(bot))
bot.add_cog(GeneralCleaner(bot))
bot.add_cog(MediaThreads(bot))
bot.add_cog(FunnyAutoResponse(bot))
bot.add_cog(InitCache(bot))
bot.add_cog(NsfwVerification(bot))

bot.run(DISCORD_TOKEN)
