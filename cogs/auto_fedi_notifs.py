import asyncio
import os

import discord
from discord.ext import tasks

from constants import CHANNEL_NEW_FEDI, ROLE_FEDI
from util.storage import get_data, set_data
from mastodon import Mastodon
from mastodon.return_types import Status

def get_latest_posts(mastodon: Mastodon) -> list[Status]:
    me = mastodon.me()
    statuses = mastodon.account_statuses(me)

    statuses = [i for i in statuses if len(i.spoiler_text) == 0]                      # posts without cw
    statuses = [i for i in statuses if i.visibility == "public"]                      # public only
    statuses = [i for i in statuses if i.in_reply_to_id is None]                      # only replies
    statuses = [i for i in statuses if i.reblog is None]                              # only renotes

    return statuses


class AutoFediNotifications(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

        Mastodon.create_app(
            'Ai',
            api_base_url='https://ice.lunya.pet',
            to_file='mastodon/clientcred.secret'
        )

        if os.path.exists("mastodon/usercred.secret"):
            self.mastodon = Mastodon(access_token="mastodon/usercred.secret")
        else:
            print("please authorize mastodon")
            exit(1)

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

        statuses = get_latest_posts(self.mastodon)
        existing_data["posted_posts"].extend([i.id for i in statuses])

        set_data("fedi_notifications", existing_data)

        self.fetch_new_posts.start()

    @tasks.loop(minutes=1)
    async def fetch_new_posts(self):
        # Fetch new fediverse posts
        statuses = get_latest_posts(self.mastodon)

        channel = self.bot.get_channel(int(CHANNEL_NEW_FEDI))
        if channel is None:
            return

        existing_data = get_data("fedi_notifications")

        for i in statuses:
            if i.id in existing_data["posted_posts"]:
                continue

            asyncio.get_event_loop().create_task(
                channel.send(
                    f"<@&{ROLE_FEDI}> Lunya posted a new note on fedi~! Go check it out~ {i.url}")
            )

            existing_data["posted_posts"].append(i.id)

        set_data("fedi_notifications", existing_data)
