import asyncio
import logging

import discord
from discord import Bot, ButtonStyle, DMChannel, GroupChannel, PartialMessageable, Thread
from discord.ui import ActionRow, Button, Container, DesignerView, Separator, TextDisplay
from sqlalchemy import delete, insert, select, update

from constants import CHANNEL_COUNTING, CHANNEL_MODERATION, GUILD
from database import (
    cache_channel,
    cache_embed,
    cache_embed_field,
    cache_message,
    cache_user,
    engine,
)
from logger import obsidian_logger


def compare_embeds(cached: int, embeds: list[discord.Embed]):
    with engine.begin() as cur:
        db_embeds = cur.execute(
            select(
                cache_embed.c.id,
                cache_embed.c.title,
                cache_embed.c.description,
                cache_embed.c.authorname,
                cache_embed.c.authoravatar,
                cache_embed.c.footertext,
            )
            .join(cache_message, cache_message.c.id == cache_embed.c.mid)
            .where(cache_message.c.mid == str(cached))
        )

        cached_embeds: list[discord.Embed] = []

        for i in db_embeds.fetchall():
            fields = cur.execute(
                select(cache_embed_field.c.name, cache_embed_field.c.value).where(
                    cache_embed_field.c.eid == i[0]
                )
            ).fetchall()

            cached_embeds.append(
                discord.Embed(
                    title=i[1],
                    description=i[2],
                    author=discord.EmbedAuthor(name=i[3], icon_url=i[4]),
                    footer=discord.EmbedFooter(text=i[5]),
                    fields=[discord.EmbedField(name=j[0], value=j[1]) for j in fields],
                )
            )

        differences: list[tuple[str, str, str]] = []

        for i, v in enumerate(zip(cached_embeds, embeds)):
            if v[0].title != v[1].title:
                differences.append((f"Embed {i + 1} Title", v[0].title, v[1].title))
            if v[0].description != v[1].description:
                differences.append(
                    (f"Embed {i + 1} Description", v[0].description, v[1].description)
                )

            if v[0].author is not None and v[1].author is not None:
                if v[0].author.name != v[1].author.name:
                    differences.append(
                        (f"Embed {i + 1} Author", v[0].author.name, v[1].author.name)
                    )

            if v[0].footer is not None and v[1].footer is not None:
                if v[0].footer.text != v[1].footer.text:
                    differences.append(
                        (f"Embed {i + 1} Footer", v[0].footer.text, v[1].footer.text)
                    )

            for j, w in enumerate(zip(v[0].fields, v[1].fields)):
                if w[0].name != w[1].name:
                    differences.append(
                        (f"Embed {i + 1} Field {j + 1} Name", w[0].name, w[1].name)
                    )
                if w[0].value != w[1].value:
                    differences.append(
                        (f"Embed {i + 1} Field {j + 1} Value", w[0].value, w[1].value)
                    )

        return differences


def get_reaction_dict(react: discord.Reaction):
    if isinstance(react.emoji, discord.PartialEmoji) or isinstance(
        react.emoji, discord.Emoji
    ):
        return {
            "emojiname": react.emoji.name,
            "emojiid": react.emoji.id,
            "emojiurl": react.emoji.url,
            "count": react.count,
        }
    elif isinstance(react.emoji, str):
        return {"emoji": react.emoji, "count": react.count}

    raise ValueError(f"Unexpected type {str(type(react))} in get_emoji_dict")


class InitCache(discord.Cog):
    def __init__(self, bot: discord.Bot):
        super().__init__()
        self.bot = bot

    async def init_channel(self, channel: discord.TextChannel):
        try:
            async for message in channel.history(limit=None):
                if self.message_is_cached(message):
                    break

                self.cache_message(message)

        except Exception:
            obsidian_logger.exception("An error occurred:")

    @discord.Cog.listener()
    async def on_ready(self):
        try:
            guild = self.bot.get_guild(int(GUILD))

            if guild is None:
                return

            obsidian_logger.info("Counting %d channels...", len(guild.text_channels))

            await asyncio.gather(*[self.init_channel(i) for i in guild.text_channels])
        except Exception:
            obsidian_logger.exception("An error occurred:")

    def message_is_cached(self, message: discord.Message) -> bool:
        with engine.begin() as cur:
            return (
                cur.execute(
                    select(cache_message.c.id).where(
                        cache_message.c.mid == str(message.id)
                    )
                ).fetchone()
                is not None
            )

    def cache_message(self, message: discord.Message):
        if (
            isinstance(message.channel, DMChannel)
            or isinstance(message.channel, GroupChannel)
            or isinstance(message.channel, PartialMessageable)
        ):
            return

        with engine.begin() as cur:
            # Cache user if not cached
            a = cur.execute(
                select(cache_user.c.id).where(
                    cache_user.c.uid == str(message.author.id)
                )
            )
            if a.fetchone() is None:
                cur.execute(
                    insert(cache_user).values(
                        uid=str(message.author.id),
                        username=message.author.name,
                        displayname=message.author.display_name,
                        avatar=message.author.display_avatar.url,
                        bot=message.author.bot,
                    )
                )
            else:
                cur.execute(
                    update(cache_user)
                    .values(
                        username=message.author.name,
                        displayname=message.author.display_name,
                        avatar=message.author.display_avatar.url,
                    )
                    .where(cache_user.c.uid == str(message.author.id))
                )

            a = cur.execute(
                select(cache_user.c.id).where(
                    cache_user.c.uid == str(message.author.id)
                )
            ).fetchone()
            if a is None:
                return
            user_id = a[0]

            # Cache channel if not cached
            a = cur.execute(
                select(cache_channel.c.id).where(
                    cache_channel.c.cid == str(message.channel.id)
                )
            ).fetchone()
            if a is None:
                topic = message.channel.__dict__.get("topic", "")
                nsfw = message.channel.__dict__.get("nsfw", False)

                cur.execute(
                    insert(cache_channel).values(
                        cid=str(message.channel.id),
                        name=message.channel.name,
                        topic=topic,
                        nsfw=nsfw,
                    )
                )
            else:
                topic = message.channel.__dict__.get("topic", "")
                nsfw = message.channel.__dict__.get("nsfw", False)

                cur.execute(
                    update(cache_channel)
                    .values(name=message.channel.name, topic=topic, nsfw=nsfw)
                    .where(cache_channel.c.cid == str(message.channel.id))
                )

            a = cur.execute(
                select(cache_channel.c.id).where(
                    cache_channel.c.cid == str(message.channel.id)
                )
            ).fetchone()

            if a is None:
                return

            channel_id = a[0]

            # Cache message if not cached
            a = cur.execute(
                select(cache_message.c.id).where(cache_message.c.mid == str(message.id))
            ).fetchone()
            if a is None:
                cur.execute(
                    insert(cache_message).values(
                        mid=str(message.id),
                        cid=channel_id,
                        uid=user_id,
                        content=message.content,
                        sentat=message.created_at,
                    )
                )
            else:
                cur.execute(
                    update(cache_message)
                    .values(content=message.content)
                    .where(cache_message.c.mid == str(message.id))
                )

            a = cur.execute(
                select(cache_message.c.id).where(cache_message.c.mid == str(message.id))
            ).fetchone()

            if a is None:
                return

            message_id = a[0]

            # Cache embeds
            for embed in message.embeds:
                cur.execute(delete(cache_embed).where(cache_embed.c.mid == message_id))

                b = cur.execute(
                    insert(cache_embed).values(
                        mid=message_id,
                        title=embed.title if embed.title else "",
                        description=embed.description if embed.description else "",
                        authorname=embed.author.name if embed.author else None,
                        authoravatar=embed.author.icon_url
                        if embed.author and embed.author.icon_url
                        else None,
                        footertext=embed.footer.text if embed.footer else None,
                    )
                )
                embed_id = b.lastrowid

                # Clear existing fields to prevent duplication
                cur.execute(
                    delete(cache_embed_field).where(cache_embed_field.c.eid == embed_id)
                )

                for field in embed.fields:
                    cur.execute(
                        insert(cache_embed_field).values(
                            eid=embed_id, name=field.name, value=field.value
                        )
                    )

    def get_cached_message(self, message_id: int):
        with engine.begin() as cur:
            a = cur.execute(
                select(
                    cache_message.c.id,
                    cache_channel.c.cid,
                    cache_user.c.uid,
                    cache_message.c.content,
                    cache_message.c.sentat,
                )
                .join(cache_channel, cache_channel.c.id == cache_message.c.cid)
                .join(cache_user, cache_user.c.id == cache_message.c.uid)
                .where(cache_message.c.mid == str(message_id))
            )
            a = a.fetchone()
            return a

    def get_cached_user(self, user_id: int):
        with engine.begin() as cur:
            a = cur.execute(
                select(
                    cache_user.c.uid,
                    cache_user.c.username,
                    cache_user.c.displayname,
                    cache_user.c.avatar,
                    cache_user.c.bot,
                ).where(cache_user.c.uid == str(user_id))
            )
            a = a.fetchone()
            return a

    @discord.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.channel.type == discord.ChannelType.private:
            return

        if message.channel.id == int(CHANNEL_COUNTING):
            return

        self.cache_message(message)

    @discord.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        try:
            changes = []

            cached = self.get_cached_message(payload.message_id)
            if not cached:
                return
            cached_author = self.get_cached_user(int(cached[2]))
            if not cached_author:
                return

            if cached_author[4] == 1:
                return

            fetched = await self.bot.get_channel(payload.channel_id).fetch_message(
                payload.message_id
            )

            if cached[3] != fetched.content:
                changes.append(("Content", cached[3], fetched.content))

            changes.extend(compare_embeds(int(cached[0]), fetched.embeds))

            if len(changes) == 0:
                return

            log_channel = self.bot.get_channel(int(CHANNEL_MODERATION))

            component = Container(
                TextDisplay("# Message Edited"),
                Separator(),
                TextDisplay("## Old Content\n\n" + 
                    "\n".join(f"{i[0]} = {i[1]}" for i in changes)),
                Separator(),
                TextDisplay("## New Content\n\n" +
                    "\n".join(f"{i[0]} = {i[2]}" for i in changes)),
                Separator(),
                ActionRow(
                    Button(label="Jump to message", style=ButtonStyle.link, url=fetched.jump_url)
                )
            )
            
            await log_channel.send(view=DesignerView(component))

            self.cache_message(fetched)
        except Exception:
            obsidian_logger.exception("An error occurred:")

    @discord.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        try:
            cached = self.get_cached_message(payload.message_id)

            if not cached:
                obsidian_logger.warning("Message not cached")
                return

            cached_author = self.get_cached_user(int(cached[2]))
            if not cached_author:
                obsidian_logger.warning("Message author not found")
                return
            if cached_author[4] == 1:
                obsidian_logger.warning("Bot message")
                return

            # Explicitly skip number messages in the counting channel
            if (
                int(payload.channel_id) == int(CHANNEL_COUNTING)
                and isinstance(cached[3], str)
                and cached[3].isnumeric()
            ):
                obsidian_logger.warning("Counting channel")
                return

            log_channel = self.bot.get_channel(int(CHANNEL_MODERATION))
            
            component = Container(
                TextDisplay("# Message Deleted"),
                Separator(),
                TextDisplay(f"## Content\n\n{cached[3]}"),
                Separator(),
                ActionRow(
                    Button(label="Jump to message", style=ButtonStyle.link, url=f"https://discord.com/channels/{payload.guild_id}/{payload.channel_id}/{payload.message_id}")
                )
            )
            
            await log_channel.send(view=DesignerView(component))
        except Exception:
            obsidian_logger.exception("An error occurred:")


def setup(bot: Bot):
    bot.add_cog(InitCache(bot))
