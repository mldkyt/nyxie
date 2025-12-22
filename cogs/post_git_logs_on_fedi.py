from discord import Bot, Cog, Message

from constants import FORGEJO_CHANNEL, FORGEJO_FEDI_TOKEN
from util.sharkey import sharkey_cache


class PostGitLogsOnFedi(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message: Message):
        if message.channel.id != int(FORGEJO_CHANNEL):
            return

        for embed in message.embeds:
            sharkey_cache.post(
                FORGEJO_FEDI_TOKEN,
                f"""{f"[{embed.title.replace('[', '').replace(']', ' - ')}]({embed.url})" if embed.url else f"{embed.title}"}

{embed.description or ""}""",
            )


def setup(bot: Bot):
    bot.add_cog(PostGitLogsOnFedi(bot))
