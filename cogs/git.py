import os

from discord import Bot, Cog, Message
from mastodon import Mastodon

from constants import CHANNEL_GIT

git_mastodon = None
if os.path.exists("data/git_usercred.secret"):
    git_mastodon = Mastodon(access_token="data/git_usercred.secret")


class Git(Cog):
    def __init__(self, bot: Bot) -> None:
        super().__init__()
        self.bot = bot

    @Cog.listener()
    async def on_message(self, msg: Message):
        assert git_mastodon is not None
        assert CHANNEL_GIT is not None

        if str(msg.channel.id) == CHANNEL_GIT and msg.webhook_id is not None:
            for embed in msg.embeds:
                post = ""
                if embed.author is not None:
                    post += f"Authored by {embed.author.name}\n\n"

                if embed.title is not None:
                    if embed.url is not None:
                        post += f"[{embed.title}]({embed.url})\n\n"
                    else:
                        post += embed.title + "\n\n"

                if embed.description is not None:
                    post += embed.description

                git_mastodon.status_post(post.strip(), visibility="unlisted")


def setup(bot: Bot):
    if git_mastodon is not None and CHANNEL_GIT is not None:
        bot.add_cog(Git(bot))
