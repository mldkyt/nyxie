import asyncio
import os

import aiohttp
import discord
import yt_dlp
from atproto import client_utils
from discord import Bot
from discord.ext import tasks
from sqlalchemy import delete, insert, select

from constants import (
    CHANNEL_NEW_VIDEOS,
    FEDI_INSTANCE,
    FEDI_TOKEN,
    ROLE_VIDEOS,
    YT_LINK,
)
from database import engine, yt_notifications_ids
from logger import ai_logger
from util.bluesky import bluesky


async def get_all_latest_post_info():
    try:
        ydl = yt_dlp.YoutubeDL()

        info = ydl.extract_info(f"{YT_LINK}/videos", download=False, process=False)
        i = 0
        output = []
        for j in info["entries"]:
            output.append(
                {
                    "id": j["id"],
                    "title": j["title"],
                    "description": j["description"],
                    "thumbnail": j["thumbnails"][-1]["url"],
                    "view_count": j["view_count"],
                }
            )

            i = i + 1
            if i > 10:
                break

        return output
    except Exception:
        ai_logger.exception("An error occurred:")
        return []


class AutoYouTubeNotifications(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.Cog.listener()
    async def on_ready(self):
        # Check if the module was initialized
        if os.path.exists("data/yt_notifications_initialized"):
            ai_logger.debug(
                "YT notifications are already initialized, starting fetch_new_posts..."
            )
            self.check_latest_videos.start()
            return

        with open("data/yt_notifications_initialized", "w") as f:
            f.write("")

        ai_logger.warning("Initializing YT notifs...")
        posts = await get_all_latest_post_info()
        with engine.begin() as cur:
            cur.execute(delete(yt_notifications_ids))

            for i in posts:
                cur.execute(insert(yt_notifications_ids).values(ytid=i["id"]))

        ai_logger.debug("Initializing YT notifs is done. Starting...")
        self.check_latest_videos.start()

    @tasks.loop(hours=1)
    async def check_latest_videos(self):
        try:
            posts = await get_all_latest_post_info()

            channel = self.bot.get_channel(int(CHANNEL_NEW_VIDEOS))

            with engine.begin() as cur:
                existing_posts = [
                    i[0]
                    for i in cur.execute(select(yt_notifications_ids.c.ytid)).fetchall()
                ]

                for i in posts:
                    if i["id"] in existing_posts:
                        continue

                    emb = discord.Embed(
                        title=i["title"],
                        description=i["description"],
                        color=discord.Color.red(),
                        url=f"https://youtube.com/watch?v={i['id']}",
                        image=i["thumbnail"],
                        fields=[
                            discord.EmbedField(
                                name="Views", value=i["view_count"], inline=True
                            )
                        ],
                    )

                    asyncio.get_event_loop().create_task(
                        channel.send(
                            f"<@&{ROLE_VIDEOS}> Lunya posted a new video~!\nClick the title of the embed or click this link~ https://youtube.com/watch?v={i['id']}",
                            embed=emb,
                        )
                    )
                    asyncio.get_event_loop().create_task(
                        bluesky.account.send_post(
                            client_utils.TextBuilder().link(
                                i["title"], f"https://youtube.com/watch?v={i['id']}"
                            )
                        )
                    )
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            f"https://{FEDI_INSTANCE}/api/notes/create",
                            json={
                                "text": f"[{i['title']}](https://youtube.com/watch?v={i['id']})"
                            },
                            headers={"Authorization": f"Bearer {FEDI_TOKEN}"},
                        ) as req:
                            if not req.ok:
                                ai_logger.warning(
                                    "Request is not an OK status! Status returned: %s",
                                    str(req.status),
                                )

                    cur.execute(insert(yt_notifications_ids).values(ytid=i["id"]))

            # Go through the history of messages and update the embeds based on information fetched
            async for msg in channel.history():
                for i in posts:
                    if i["id"] in msg.content:
                        # Update the embed
                        emb = discord.Embed(
                            title=i["title"],
                            description=i["description"],
                            color=discord.Color.red(),
                            url=f"https://youtube.com/watch?v={i['id']}",
                            image=i["thumbnail"],
                            fields=[
                                discord.EmbedField(
                                    name="Views", value=i["view_count"], inline=True
                                )
                            ],
                        )

                        asyncio.get_event_loop().create_task(msg.edit(embed=emb))
        except Exception:
            ai_logger.exception("An error occurred:")


def setup(bot: Bot):
    bot.add_cog(AutoYouTubeNotifications(bot))
