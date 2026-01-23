import aiohttp
from discord import Bot, Cog, Message

from constants import FEDI_INSTANCE, FORGEJO_CHANNEL, FORGEJO_FEDI_TOKEN
from logger import obsidian_logger


class PostGitLogsOnFedi(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message: Message):
        if message.channel.id != int(FORGEJO_CHANNEL):
            return

        for embed in message.embeds:
            if not isinstance(embed.title, str):
                continue

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"https://{FEDI_INSTANCE}/api/notes/create",
                    json={
                        "text": f"""{f"[{embed.title.replace('[', '').replace(']', ' - ')}]({embed.url})" if embed.url else f"{embed.title}"}

    {embed.description or ""}"""
                    },
                    headers={"Authorization": f"Bearer {FORGEJO_FEDI_TOKEN}"},
                ) as req:
                    if not req.ok:
                        obsidian_logger.warning(
                            "Request is not an OK status! Status returned: %s",
                            str(req.status),
                        )


def setup(bot: Bot):
    bot.add_cog(PostGitLogsOnFedi(bot))
