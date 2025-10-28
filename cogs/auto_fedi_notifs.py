import asyncio

import aiohttp
import discord
from discord import Bot
from discord.ext import tasks
from mastodon import Mastodon

from constants import CHANNEL_NEW_FEDI, ROLE_FEDI, FEDI_INSTANCE
from util.storage import get_data, set_data

mastodon = Mastodon(access_token='data/usercred', api_base_url=f'https://{FEDI_INSTANCE}')

def get_latest_posts():
    me = mastodon.me()
    posts = mastodon.account_statuses(me)

    posts = [i for i in posts if not i.sensitive]           # posts without cw
    posts = [i for i in posts if i.visibility == "public"]  # public posts only
    posts = [i for i in posts if i.in_reply_to_id is None]  # no replies
    posts = [i for i in posts if i.reblog is None]          # no boosts

    return posts


class AutoFediNotifications(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.Cog.listener()
    async def on_ready(self):
        # Fetch existing data
        existing_data = get_data("fedi_notifications")

        # Check if the module was initialized
        if existing_data.get("initialized", False):
            self.fetch_new_posts.start()
            return

        existing_data["initialized"] = True
        existing_data["posted_posts"] = []

        posts = get_latest_posts()
        existing_data["posted_posts"].extend([i.id for i in posts])

        set_data("fedi_notifications", existing_data)

        self.fetch_new_posts.start()

    @tasks.loop(minutes=1)
    async def fetch_new_posts(self):
        # Fetch new fediverse posts
        posts = get_latest_posts()

        channel = self.bot.get_channel(int(CHANNEL_NEW_FEDI))
        if channel is None:
            return

        existing_data = get_data("fedi_notifications")

        for i in posts:
            if i.id in existing_data["posted_posts"]:
                continue

            asyncio.get_event_loop().create_task(
                channel.send(
                    f"<@&{ROLE_FEDI}> Lunya posted a new post on fedi~! Go check it out~ {i.url}")
            )

            existing_data["posted_posts"].append(i.id)

        set_data("fedi_notifications", existing_data)

def setup(bot: Bot):
    bot.add_cog(AutoFediNotifications(bot))
