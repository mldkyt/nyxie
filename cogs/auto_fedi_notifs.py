import asyncio
import os

import discord
from discord import Bot, TextChannel
from discord.ext import tasks
from sqlalchemy import delete, insert, select

from constants import CHANNEL_NEW_FEDI, FEDI_INSTANCE, ROLE_FEDI
from database import engine, fedi_notifications_ids
from logger import obsidian_logger
from util.sharkey import sharkey_cache


async def get_latest_posts():
    posts = await sharkey_cache.get_latest_posts()

    posts = [
        i for i in posts if i["cw"] is None or len(i["cw"]) == 0
    ]  # posts without cw
    posts = [i for i in posts if i["visibility"] == "public"]  # public posts only
    posts = [i for i in posts if "reply" not in i or i["reply"] is None]  # no replies
    posts = [i for i in posts if "renote" not in i or i["renote"] is None]  # no boosts

    return [i["id"] for i in posts]


class AutoFediNotifications(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.Cog.listener()
    async def on_ready(self):
        await self.on_ready_discord()

    async def on_ready_discord(self):
        # Check if the module was initialized
        if os.path.exists("data/fedi_notifications_initialized"):
            obsidian_logger.debug(
                "Fedi notifications are already initialized, starting fetch_new_posts..."
            )
            self.fetch_new_posts.start()
            return

        with open("data/fedi_notifications_initialized", "w") as f:
            f.write("")

        obsidian_logger.warning("Initializing fedi notifs...")

        posts = await get_latest_posts()
        with engine.begin() as cur:
            cur.execute(delete(fedi_notifications_ids))

            for i in posts:
                cur.execute(insert(fedi_notifications_ids).values(aid=i))

        obsidian_logger.debug("Initializing fedi notifs is done. Starting...")
        self.fetch_new_posts.start()

    @tasks.loop(minutes=1)
    async def fetch_new_posts(self):
        if not isinstance(CHANNEL_NEW_FEDI, str):
            return

        # Fetch new fediverse posts
        posts = await get_latest_posts()

        channel = self.bot.get_channel(int(CHANNEL_NEW_FEDI))
        if channel is None or not isinstance(channel, TextChannel):
            return

        with engine.begin() as cur:
            existing_data = [
                i[0]
                for i in cur.execute(select(fedi_notifications_ids.c.aid)).fetchall()
            ]

            for i in posts:
                if i in existing_data:
                    continue

                asyncio.get_event_loop().create_task(
                    channel.send(
                        f"<@&{ROLE_FEDI}> Lunya posted a new note on fedi~! Go check it out~ https://{FEDI_INSTANCE}/notes/{i}"
                    )
                )

                cur.execute(insert(fedi_notifications_ids).values(aid=i))


def setup(bot: Bot):
    bot.add_cog(AutoFediNotifications(bot))
