import os

import discord
from discord import Bot, ButtonStyle, TextChannel, MediaGalleryItem
from discord.ext import tasks
from discord.ui import Container, TextDisplay, Button, Separator, MediaGallery, DesignerView, ActionRow
from markdownify import markdownify
from mastodon.return_types import Status
from sqlalchemy import delete, insert, select

from constants import CHANNEL_NEW_FEDI, ROLE_FEDI, VERSION
from database import engine, fedi_notifications_ids
from logger import obsidian_logger
from util.akkoma import akkoma_cache


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

        obsidian_logger.warning("Initializing fedi notifs...")

        posts = get_latest_akkoma_posts()
        with engine.begin() as cur:
            cur.execute(delete(fedi_notifications_ids))

            for i in posts:
                cur.execute(insert(fedi_notifications_ids).values(aid=i.id))

        with open("data/fedi_notifications_initialized", "w") as f:
            f.write("")

        obsidian_logger.debug("Initializing fedi notifs is done. Starting...")
        self.fetch_new_posts.start()

    @tasks.loop(minutes=1)
    async def fetch_new_posts(self):
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


def setup(bot: Bot):
    bot.add_cog(AutoFediNotifications(bot))
