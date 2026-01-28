import asyncio
import os
import re

import aiohttp
import discord
from discord import Bot, TextChannel
from discord.ext import tasks
from sqlalchemy import delete, insert, select

from constants import CHANNEL_NEW_FEDI, FEDI_INSTANCE, ROLE_FEDI, ATPROTO_EMAIL, ATPROTO_PASSWORD, ATPROTO_CHANNEL
from database import bsky_posted, engine, fedi_notifications_ids
from logger import obsidian_logger
from util.bluesky import bluesky
from util.sharkey import sharkey_cache


async def get_latest_posts_bsky():
    posts = await sharkey_cache.get_latest_posts()

    posts = [
        i for i in posts if i["cw"] is None or len(i["cw"]) == 0
    ]  # posts without cw
    posts = [i for i in posts if i["visibility"] == "public"]  # public posts only
    posts = [i for i in posts if "reply" not in i or i["reply"] is None]  # no replies
    posts = [
        i for i in posts if "renote" not in i or i["renote"] is None
    ]  # no boosts/quotes
    posts = [i for i in posts if "poll" not in i or i["poll"] is None]  # no polls
    posts = [
        i
        for i in posts
        if "text" in i and i["text"] is not None and len(i["text"]) < 300
    ]  # max 300 letters
    posts = [
        i for i in posts if not re.match(r":[a-zA-Z\-_]+:", i["text"])
    ]  # no custom emojis

    return posts


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
        if ATPROTO_EMAIL is not None and ATPROTO_PASSWORD is not None and ATPROTO_CHANNEL is not None:
            await self.on_ready_bsky()

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

    async def on_ready_bsky(self):
        # Check if the module was initialized
        if os.path.exists("data/fedi_notifications_bsky_initialized"):
            obsidian_logger.debug(
                "Bsky posting is already initialized, starting fetch_new_posts_bsky..."
            )
            self.fetch_new_posts_bsky.start()
            return

        with open("data/fedi_notifications_bsky_initialized", "w") as f:
            f.write("")

        obsidian_logger.warning("Initializing bsky posting...")

        posts = await get_latest_posts()
        with engine.begin() as cur:
            cur.execute(delete(bsky_posted))

            for i in posts:
                cur.execute(insert(bsky_posted).values(aid=i))

        obsidian_logger.debug("Initializing bsky posting is done. Starting...")
        self.fetch_new_posts_bsky.start()

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

    @tasks.loop(minutes=1)
    async def fetch_new_posts_bsky(self):
        posts = await get_latest_posts_bsky()

        for i in posts:
            try:
                with engine.begin() as c:
                    if (
                        c.execute(
                            select(bsky_posted.c.id).where(bsky_posted.c.aid == i["id"])
                        ).fetchone()
                        is not None
                    ):
                        continue

                    is_video = False
                    images = []
                    alt_texts = []

                    # Files
                    if "files" in i and i["files"] is not None and len(i["files"]) > 0:
                        # Video
                        if i["files"][0]["type"].startswith("video"):
                            is_video = True
                            async with aiohttp.ClientSession() as session:
                                async with session.get(i["files"][0]["url"]) as req:
                                    if not req.ok:
                                        continue

                                    images.append(await req.read())
                                    alt_texts.append(
                                        i["files"][0]["comment"]
                                        if "comment" in i["files"][0]
                                        and i["files"][0]["comment"] is not None
                                        and len(i["files"][0]["comment"].strip()) > 0
                                        else i["files"][0]["name"]
                                    )
                        else:
                            for j in i["files"]:
                                if not j["type"].startswith("image"):
                                    continue

                                async with aiohttp.ClientSession() as session:
                                    async with session.get(j["url"]) as req:
                                        if not req.ok:
                                            continue

                                        images.append(await req.read())
                                        alt_texts.append(
                                            j["comment"]
                                            if "comment" in j
                                            and j["comment"] is not None
                                            and len(j["comment"].strip()) > 0
                                            else j["name"]
                                        )

                    # Wait for login
                    while not bluesky.logged_in:
                        obsidian_logger.debug("[Fedi>Bluesky Posts]Waiting for login")
                        await asyncio.sleep(1)

                    # Post
                    if len(images) == 0:
                        bluesky.queue(i["text"])
                    elif is_video:
                        bluesky.queue_video(
                            text=i["text"], video=images[0], video_alt=alt_texts[0]
                        )
                    else:
                        bluesky.queue_images(
                            text=i["text"], images=images, image_alts=alt_texts
                        )
                    obsidian_logger.debug("[Fedi>Bluesky Posts]Posted %s to fedi", i["id"])

                    c.execute(insert(bsky_posted).values(aid=i["id"]))

            except Exception:
                obsidian_logger.exception("Exception while posting on Bluesky")


def setup(bot: Bot):
    bot.add_cog(AutoFediNotifications(bot))
