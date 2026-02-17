import asyncio
import os

from aiohttp import ClientSession
import discord
from discord import Bot, ButtonStyle, TextChannel, MediaGalleryItem
from discord.ui import Container, TextDisplay, Button, Separator, MediaGallery, DesignerView, ActionRow
from discord.ext import tasks
from sqlalchemy import delete, insert, select

from constants import CHANNEL_NEW_FEDI, FEDI_INSTANCE, FEDI_TOKEN, ROLE_FEDI, VERSION
from database import engine, fedi_notifications_ids
from logger import obsidian_logger
from util.sharkey import sharkey_cache
from util.akkoma import akkoma_cache
from mastodon.return_types import Status
from markdownify import markdownify


async def get_latest_sharkey_posts():
    posts = await sharkey_cache.get_latest_posts()

    posts = [
        i for i in posts if i["cw"] is None or len(i["cw"]) == 0
    ]  # posts without cw
    posts = [i for i in posts if i["visibility"] == "public"]  # public posts only
    posts = [i for i in posts if "reply" not in i or i["reply"] is None]  # no replies
    posts = [i for i in posts if "renote" not in i or i["renote"] is None]  # no boosts

    return [i["id"] for i in posts]

def get_latest_akkoma_posts() -> list[Status]:
    posts = akkoma_cache.get_latest_posts()

    posts = [i for i in posts if len(i.spoiler_text) == 0] # posts without cw
    posts = [i for i in posts if i.visibility == "public"] # only public posts
    posts = [i for i in posts if i.reblog is None] # no boosts
    posts = [i for i in posts if i.in_reply_to_id is None] # no replies

    return posts


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

        posts = await get_latest_sharkey_posts()
        with engine.begin() as cur:
            cur.execute(delete(fedi_notifications_ids))

            for i in posts:
                cur.execute(insert(fedi_notifications_ids).values(aid=i))

        obsidian_logger.debug("Initializing fedi notifs is done. Starting...")
        self.fetch_new_posts.start()

    @tasks.loop(minutes=1)
    async def fetch_new_posts(self):
        await self.fetch_new_sharkey_posts()
        await self.fetch_new_akkoma_posts()

    async def fetch_new_akkoma_posts(self):
        if not isinstance(CHANNEL_NEW_FEDI, str):
            return

        posts = get_latest_akkoma_posts()

        channel = self.bot.get_channel(int(CHANNEL_NEW_FEDI))
        if channel is None or not isinstance(channel, TextChannel):
            return

        with engine.begin() as cur:
            existing_data = [
                i[0]
                for i in cur.execute(select(fedi_notifications_ids.c.aid)).fetchall()
            ]

            for i in posts:
                if i.id in existing_data:
                    continue

                items = []

                text = markdownify(i.content)
                if len(text) > 0:
                    items.append(
                        TextDisplay(text)
                    )

                if len(i.media_attachments) > 0:
                    items.append(
                        MediaGallery(
                            *[MediaGalleryItem(j.url, description=j.description, spoiler=i.sensitive or len(i.spoiler_text) > 0) for j in i.media_attachments]
                        )
                    )

                component = Container(
                    TextDisplay("# New Fedi Post"),
                    Separator(),
                    *items,
                    Separator(),
                    ActionRow(
                        Button(label="View on fedi", style=ButtonStyle.url, url=i.url or i.uri)
                    ),
                    TextDisplay(f"-# obsidian {VERSION} || <@&{ROLE_FEDI}>")
                )

                await channel.send(
                    view=DesignerView(component)
                )

                cur.execute(insert(fedi_notifications_ids).values(aid=i.id))

    async def fetch_new_sharkey_posts(self):
        if not isinstance(CHANNEL_NEW_FEDI, str):
            return

        # Fetch new fediverse posts
        posts = await get_latest_sharkey_posts()

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

                async with ClientSession() as sess:
                    async with sess.post(f"https://{FEDI_INSTANCE}/api/notes/show", json={
                        "noteId": i
                    }, headers={
                        "Authorization": f"Bearer {FEDI_TOKEN}"
                    }) as req:
                        if not req.ok:
                            obsidian_logger.error("Failed to get just posted post %s: %d %s", i, req.status, await req.text())
                            continue

                        data = await req.json()

                items = []

                if data['text'] is not None and len(data['text']) > 0:
                    items.append(
                        TextDisplay(data['text'])
                    )

                if data['files'] is not None and len(data['files']) > 0:
                    items.append(
                        MediaGallery(
                            *[MediaGalleryItem(i['url'], description=i['comment'], spoiler=i['isSensitive']) for i in data['files']]
                        )
                    )

                component = Container(
                    TextDisplay("# New Fedi Post"),
                    Separator(),
                    *items,
                    Separator(),
                    ActionRow(
                        Button(label="View on fedi", style=ButtonStyle.url, url=f"https://{FEDI_INSTANCE}/notes/{i}")
                    ),
                    TextDisplay(f"-# obsidian {VERSION} || <@&{ROLE_FEDI}>")
                )

                await channel.send(
                    view=DesignerView(component)
                )

                cur.execute(insert(fedi_notifications_ids).values(aid=i))


def setup(bot: Bot):
    bot.add_cog(AutoFediNotifications(bot))
