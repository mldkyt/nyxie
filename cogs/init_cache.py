import asyncio
import logging

import discord
import sqlite3

from constants import GUILD, CHANNEL_MODERATION, CHANNEL_COUNTING

ai_logger = logging.getLogger("ai")

database = sqlite3.connect("data/cache.sqlite3")

def init_db():
    cur = database.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS channel (
    	id INTEGER PRIMARY KEY AUTOINCREMENT,
    	channelid TEXT NOT NULL,
    	name TEXT NOT NULL,
    	topic TEXT NOT NULL,
    	announcement INTEGER DEFAULT (0) NOT NULL,
    	nsfw INTEGER DEFAULT (0) NOT NULL
    );""")

    cur.execute("""CREATE TABLE IF NOT EXISTS "user" (
    	id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    	userid TEXT NOT NULL,
    	username TEXT NOT NULL,
    	displayname TEXT NOT NULL,
    	avatar TEXT NOT NULL,
    	bot INTEGER DEFAULT (0) NOT NULL
    );""")

    cur.execute("""CREATE TABLE IF NOT EXISTS message (
    	id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    	messageid TEXT NOT NULL,
    	channelid INTEGER NOT NULL,
    	authorid INTEGER NOT NULL,
    	content TEXT NOT NULL,
    	sentat TEXT NOT NULL,
    	CONSTRAINT message_channel_FK FOREIGN KEY (channelid) REFERENCES channel(id) ON DELETE CASCADE ON UPDATE CASCADE,
    	CONSTRAINT message_user_FK FOREIGN KEY (authorid) REFERENCES "user"(id) ON DELETE CASCADE ON UPDATE CASCADE
    );""")

    cur.execute("""CREATE TABLE IF NOT EXISTS reactions (
    	id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    	messageid INTEGER NOT NULL,
    	emojiname TEXT NOT NULL,
    	emojiid TEXT,
    	emojiurl TEXT,
    	count INTEGER DEFAULT (0) NOT NULL,
    	CONSTRAINT reactions_message_FK FOREIGN KEY (messageid) REFERENCES message(id)
    );""")

    cur.execute("""CREATE TABLE IF NOT EXISTS embed (
    	id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    	messageid INTEGER NOT NULL,
    	title TEXT NOT NULL,
    	description TEXT NOT NULL,
    	authorname TEXT,
    	authoravatar TEXT,
    	footertext TEXT,
    	CONSTRAINT embed_message_FK FOREIGN KEY (messageid) REFERENCES message(id)
    );""")

    cur.execute("""CREATE TABLE IF NOT EXISTS embedfield (
    	id INTEGER PRIMARY KEY AUTOINCREMENT,
    	embedid INTEGER NOT NULL,
    	name TEXT NOT NULL,
    	value TEXT NOT NULL,
    	CONSTRAINT embedfield_embed_FK FOREIGN KEY (embedid) REFERENCES embed(id)
    );""")

    cur.close()
    database.commit()

def compare_embeds(cached: int, embeds: list[discord.Embed]):
    cur = database.cursor()
    cur.execute("SELECT * FROM embed WHERE messageid = (SELECT id FROM message WHERE messageid = ?);", (str(cached),))

    cached_embeds: list[discord.Embed] = []

    for i in cur.fetchall():
        cur.execute("SELECT * FROM embedfield WHERE embedid = ?;", (i[0],))
        fields = cur.fetchall()

        cached_embeds.append(discord.Embed(
            title=i[2],
            description=i[3],
            author=discord.EmbedAuthor(
                name=i[4],
                icon_url=i[5]
            ),
            footer=discord.EmbedFooter(
                text=i[6]
            ),
            fields=[discord.EmbedField(name=j[2], value=j[3]) for j in fields]
        ))

    differences: list[tuple[str, str, str]] = []

    for (i, v) in enumerate(zip(cached_embeds, embeds)):
        if v[0].title != v[1].title:
            differences.append((f"Embed {i + 1} Title", v[0].title, v[1].title))
        if v[0].description != v[1].description:
            differences.append((f"Embed {i + 1} Description", v[0].description, v[1].description))

        if v[0].author is not None and v[1].author is not None:
            if v[0].author.name != v[1].author.name:
                differences.append((f"Embed {i + 1} Author", v[0].author.name, v[1].author.name))

        if v[0].footer is not None and v[1].footer is not None:
            if v[0].footer.text != v[1].footer.text:
                differences.append((f"Embed {i + 1} Footer", v[0].footer.text, v[1].footer.text))

        for (j, w) in enumerate(zip(v[0].fields, v[1].fields)):
            if w[0].name != w[1].name:
                differences.append((f"Embed {i + 1} Field {j + 1} Name", w[0].name, w[1].name))
            if w[0].value != w[1].value:
                differences.append((f"Embed {i + 1} Field {j + 1} Value", w[0].value, w[1].value))

    return differences


def get_reaction_dict(react: discord.Reaction):
    if isinstance(react.emoji, discord.PartialEmoji) or isinstance(react.emoji, discord.Emoji):
        return {
            "emojiname": react.emoji.name,
            "emojiid": react.emoji.id,
            "emojiurl": react.emoji.url,
            "count": react.count
        }
    elif isinstance(react.emoji, str):
        return {
            "emoji": react.emoji,
            "count": react.count
        }

    raise ValueError(f"Unexpected type {str(type(react))} in get_emoji_dict")


class InitCache(discord.Cog):
    def __init__(self, bot: discord.Bot):
        super().__init__()
        init_db()
        self.bot = bot

    async def init_channel(self, channel: discord.TextChannel):
        try:
            async for message in channel.history(limit=None):
                if self.message_is_cached(message):
                    break

                self.cache_message(message)

            ai_logger.info(f"Caching channel #%s finished.", channel.name)
        except Exception as e:
            ai_logger.exception("An error occurred:")

    @discord.Cog.listener()
    async def on_ready(self):
        try:
            guild = self.bot.get_guild(int(GUILD))

            if guild is None:
                return

            ai_logger.info("Counting %d channels...", len(guild.text_channels))

            await asyncio.gather(
                *[self.init_channel(i) for i in guild.text_channels]
            )
        except Exception as e:
            ai_logger.exception("An error occurred:")

    def message_is_cached(self, message: discord.Message) -> bool:
        cur = database.cursor()
        cur.execute("SELECT id FROM message WHERE messageid = ?;", (str(message.id),))
        a = cur.fetchone()
        cur.close()

        return a is not None

    def cache_message(self, message: discord.Message):
        cur = database.cursor()

        # Cache user if not cached
        cur.execute("SELECT id FROM \"user\" WHERE userid = ?;", (str(message.author.id),))
        if cur.fetchone() is None:
            cur.execute("INSERT INTO \"user\" (userid, username, displayname, avatar, bot) VALUES(?, ?, ?, ?, ?);",
                (str(message.author.id), message.author.name, message.author.display_name, message.author.display_avatar.url, 1 if message.author.bot else 0))
        else:
            cur.execute("UPDATE \"user\" SET username = ?, displayname = ?, avatar = ?, bot = ? WHERE userid = ?;",
                (message.author.name, message.author.display_name, message.author.display_avatar.url, 1 if message.author.bot else 0, str(message.author.id)))
        cur.execute("SELECT id FROM \"user\" WHERE userid = ?;", (str(message.author.id),))
        user_id = cur.fetchone()[0]

        # Cache channel if not cached
        cur.execute("SELECT id FROM channel WHERE channelid = ?;", (str(message.channel.id),))
        if cur.fetchone() is None:
            cur.execute("INSERT INTO channel (channelid, name, topic, announcement, nsfw) VALUES(?, ?, ?, ?, ?);",
                (str(message.channel.id), message.channel.name, "" if message.channel.topic is None else message.channel.topic, 1 if message.channel.type == discord.ChannelType.news else 0,
                    1 if message.channel.nsfw else 0))
        else:
            cur.execute("UPDATE channel SET name = ?, topic = ?, announcement = ?, nsfw = ? WHERE channelid = ?;", (message.channel.name, "" if message.channel.topic is None else message.channel.topic, 1 if message.channel.type == discord.ChannelType.news else 0,
                1 if message.channel.nsfw else 0, str(message.channel.id)))
        cur.execute("SELECT id FROM channel WHERE channelid = ?;", (str(message.channel.id),))
        channel_id = cur.fetchone()[0]

        # Cache message if not cached
        cur.execute("SELECT id FROM message WHERE messageid = ?;", (str(message.id),))
        if cur.fetchone() is None:
            cur.execute("INSERT INTO message (messageid, channelid, authorid, content, sentat) VALUES(?, ?, ?, ?, ?);",
                (str(message.id), channel_id, user_id, message.content, message.created_at.isoformat()))
        else:
            cur.execute("UPDATE message SET content = ? WHERE messageid = ?;", (message.content, str(message.id)))
        cur.execute("SELECT id FROM message WHERE messageid = ?;", (str(message.id),))
        message_id = cur.fetchone()[0]

        # Cache reactions
        for reaction in message.reactions:
            cur.execute("SELECT id FROM reactions WHERE messageid = ? AND emojiname = ?;", (str(message.id), reaction.emoji.id if isinstance(reaction.emoji, (discord.Emoji, discord.PartialEmoji)) else str(reaction.emoji)))
            if cur.fetchone() is None:
                cur.execute("INSERT INTO reactions (messageid, emojiname, emojiid, emojiurl, count) VALUES (?, ?, ?, ?, ?);",
                    (message_id, str(reaction.emoji), reaction.emoji.id if isinstance(reaction.emoji, (discord.Emoji, discord.PartialEmoji)) else reaction.emoji,
                        reaction.emoji.url if isinstance(reaction.emoji, (discord.Emoji, discord.PartialEmoji)) else None, reaction.count))
            else:
                cur.execute("UPDATE reactions SET emojiurl = ?, count = ? WHERE messageid = ? AND emojiid = ?",
                    (reaction.emoji.url if isinstance(reaction.emoji, (discord.Emoji, discord.PartialEmoji)) else None, reaction.count,
                        message_id, reaction.emoji.id if isinstance(reaction.emoji, (discord.Emoji, discord.PartialEmoji)) else reaction.emoji))

        # Cache embeds
        for embed in message.embeds:
            cur.execute("DELETE FROM embed WHERE messageid = ?;", (str(message.id),))
            cur.execute(
                "INSERT INTO embed (messageid, title, description, authorname, authoravatar, footertext) VALUES(?, ?, ?, ?, ?, ?);",
                (message_id,
                    embed.title if embed.title else "",
                    embed.description if embed.description else "",
                    embed.author.name if embed.author else None,
                    embed.author.icon_url if embed.author and embed.author.icon_url else None,
                    embed.footer.text if embed.footer else None))
            embed_id = cur.lastrowid

            # Clear existing fields to prevent duplication
            cur.execute("DELETE FROM embedfield WHERE embedid = ?", (embed_id,))

            for field in embed.fields:
                cur.execute(
                    "INSERT OR REPLACE INTO embedfield (embedid, name, value) VALUES(?, ?, ?);",
                    (embed_id, field.name, field.value))

        database.commit()
        cur.close()

    def get_cached_message(self, message_id: int) -> tuple[str, str, str, str, str]:
        cur = database.cursor()
        cur.execute("""SELECT messageid, channel.channelid, \"user\".userid, content, sentat
            FROM message
            JOIN channel ON channel.id = message.channelid
            JOIN \"user\" ON \"user\".id = message.authorid
            WHERE messageid = ?;""", (str(message_id),))
        a = cur.fetchone()
        cur.close()
        return a

    def get_cached_user(self, user_id: int) -> tuple[str, str, str, str, int]:
        cur = database.cursor()
        cur.execute("""SELECT userid, username, displayname, avatar, bot
            FROM \"user\"
            WHERE userid = ?;""", (str(user_id),))
        a = cur.fetchone()
        cur.close()
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

            fetched = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)

            if cached[3] != fetched.content:
                changes.append(("Content", cached[3], fetched.content))

            changes.extend(compare_embeds(int(cached[0]), fetched.embeds))

            if len(changes) == 0:
                return

            log_channel = self.bot.get_channel(int(CHANNEL_MODERATION))

            await log_channel.send(embed=discord.Embed(
                title="Message Edited",
                color=discord.Color.yellow(),
                description="A message has been edited.",
                fields=[*[discord.EmbedField(name=i[0], value=f"{i[1]} -> {i[2]}") for i in changes],
                        discord.EmbedField(name="Link", value=f"[Jump]({fetched.jump_url})")]
            ))

            self.cache_message(fetched)
        except Exception as e:
            ai_logger.exception("An error occurred:")

    @discord.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        try:
            cached = self.get_cached_message(payload.message_id)

            if not cached:
                ai_logger.warning("Message not cached")
                return

            cached_author = self.get_cached_user(int(cached[2]))
            if not cached_author:
                ai_logger.warning("Message author not found")
                return
            if cached_author[4] == 1:
                ai_logger.warning("Bot message")
                return

            # Explicitly skip number messages in the counting channel
            if int(payload.channel_id) == int(CHANNEL_COUNTING) \
                    and isinstance(cached[3], str) \
                    and cached[3].isnumeric():
                ai_logger.warning("Counting channel")
                return

            log_channel = self.bot.get_channel(int(CHANNEL_MODERATION))

            await log_channel.send(embed=discord.Embed(
                title="Message Deleted",
                color=discord.Color.red(),
                description="A message has been deleted.\n\n"
                            f"{cached[3]}",
                fields=[
                    discord.EmbedField(name="Link", value=f"[Jump](https://discord.com/channels/{payload.guild_id}/{payload.channel_id}/{payload.message_id})")
                ]
            ))
        except Exception as e:
            ai_logger.exception("An error occurred:")
