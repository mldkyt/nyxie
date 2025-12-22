from discord import Bot, Cog
from discord.ext.tasks import loop

from constants import ai_logger
from util.sharkey import sharkey_cache


class JobQueue(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        super().__init__()

    @Cog.listener()
    async def on_ready(self):
        self.job_queue_sharkey.start()

    @loop(seconds=30)
    async def job_queue_sharkey(self):
        await sharkey_cache.send_next_post()
        ai_logger.debug(sharkey_cache.get_job_stats())


def setup(bot: Bot):
    bot.add_cog(JobQueue(bot))
