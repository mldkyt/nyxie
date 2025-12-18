import aiohttp
from discord import Cog, Bot, Message

from constants import FORGEJO_CHANNEL, FEDI_INSTANCE, FORGEJO_FEDI_TOKEN


class PostGitLogsOnFedi(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message: Message):
        if message.channel.id != int(FORGEJO_CHANNEL):
            return

        for embed in message.embeds:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"https://{FEDI_INSTANCE}/api/notes/create", headers={
                    "Authorization": f"Bearer {FORGEJO_FEDI_TOKEN}"
                }, json={
                    "text": f"""{f"[{embed.title.replace('[', '').replace(']', ' - ')}]({embed.url})" if embed.url else f"{embed.title}"}

{embed.description or ""}"""
                }):
                    pass

def setup(bot: Bot):
    bot.add_cog(PostGitLogsOnFedi(bot))
