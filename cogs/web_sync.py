from discord import Cog, Bot

from constants import GUILD
from logger import obsidian_logger
from util.web_sync import add_message


class WebSync(Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        guild = self.bot.get_guild(int(GUILD))
        for channel in guild.text_channels:
            if channel.permissions_for(guild.default_role).read_messages:
                async for message in channel.history(limit=1000):
                    try:
                        await add_message(message)
                    except Exception:
                        obsidian_logger.exception("Failed to add message to web UI:")


def setup(bot: Bot):
    bot.add_cog(WebSync(bot))
