from atproto import AtUri
from discord import (
    Bot,
    Cog,
    Embed,
    EmbedAuthor,
    EmbedField,
    Guild,
    Message,
    RawReactionActionEvent,
    TextChannel,
)
from discord.ext.tasks import loop
from sqlalchemy import insert, select

from constants import ATPROTO_CHANNEL, GUILD, ATPROTO_EMAIL, ATPROTO_PASSWORD
from database import bsky_posts, engine
from logger import obsidian_logger
from util.bluesky import bluesky


class Bluesky(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        super().__init__()

    @Cog.listener()
    async def on_ready(self):
        bluesky_channel = await self.bot.fetch_channel(ATPROTO_CHANNEL)
        await bluesky.log_in(bluesky_channel)

        self.check_notifications.start()
        self.post_queue.start()

    @Cog.listener()
    async def on_message(self, message: Message):
        if not isinstance(message.guild, Guild):
            obsidian_logger.debug("Bluesky notifs Guild does not exist")
            return

        if message.channel.id != int(ATPROTO_CHANNEL):
            return

        await self.on_message_reply(message)

    async def on_message_reply(self, message: Message):
        # Handle replies
        if message.reference is None:
            return
        if message.reference.message_id is None:
            return

        with engine.begin() as c:
            a = c.execute(
                select(bsky_posts.c.did).where(
                    bsky_posts.c.mid == str(message.reference.message_id)
                )
            ).fetchone()

        if a is None:
            return

        at = AtUri.from_str(a[0])

        try:
            post_to_reply_to = await bluesky.account.get_post(
                at.rkey, profile_identify=at.host
            )
        except Exception:
            await message.add_reaction("❌")
            return

        bluesky.queue_reply(message.content, post_to_reply_to.uri, post_to_reply_to.cid)

        await message.add_reaction("✅")

    @Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        try:
            if (
                payload.guild_id is None
                or payload.channel_id is None
                or payload.message_id is None
            ):
                return
            if payload.guild_id != int(GUILD) or payload.channel_id != int(
                ATPROTO_CHANNEL
            ):
                return

            with engine.begin() as c:
                a = c.execute(
                    select(bsky_posts.c.did).where(
                        bsky_posts.c.mid == str(payload.message_id)
                    )
                ).fetchone()

            if a is None:
                return

            at = AtUri.from_str(a[0])

            try:
                post_to_reply_to = await bluesky.account.get_post(
                    at.rkey, profile_identify=at.host
                )
            except Exception:
                obsidian_logger.error(
                    "Unable to like post %s on bsky, error fetching post", at.rkey
                )
                return

            if post_to_reply_to.cid is None:
                obsidian_logger.error(
                    "Unable to like post %s on bsky, HOW THE FUCK CAN AN ID BE NULL??????",
                    at.rkey,
                )
                return

            if payload.emoji.is_unicode_emoji() and (
                payload.emoji == "❤️" or payload.emoji == "⭐"
            ):
                await bluesky.account.like(post_to_reply_to.uri, post_to_reply_to.cid)
            elif payload.emoji.is_unicode_emoji() and payload.emoji == "🚀":
                bluesky.queue_repost(
                    repost_uri=post_to_reply_to.uri, repost_cid=post_to_reply_to.cid
                )
        except Exception:
            obsidian_logger.exception("Failed to like bsky post: ")

    @loop(seconds=120)
    async def check_notifications(self):
        guild = self.bot.get_guild(int(GUILD))
        if not isinstance(guild, Guild):
            obsidian_logger.debug("Bluesky notifs Guild does not exist")
            return

        channel = guild.get_channel(int(ATPROTO_CHANNEL))
        if not isinstance(channel, TextChannel):
            obsidian_logger.debug("Bluesky notifs ATproto channel is not valid")
            return

        async for notif in bluesky.notifications():
            try:
                post_it_replied_to = await bluesky.account.get_post(
                    AtUri.from_str(notif.record.reply.parent.uri).rkey
                )
            except Exception:
                obsidian_logger.debug(
                    "Bluesky notifs Skipping reply: Unable to fetch reply"
                )
                return

            message_reply = await channel.send(
                embed=Embed(
                    fields=[
                        EmbedField(
                            name="Post", value=post_it_replied_to.value.text
                        ),
                        EmbedField(name="Reply", value=notif.record.text),
                    ],
                    author=EmbedAuthor(
                        name=notif.author.display_name
                             or str(notif.author.handle),
                        icon_url=str(notif.author.avatar),
                    ),
                )
            )

            with engine.begin() as c:
                c.execute(
                    insert(bsky_posts).values(
                        mid=str(message_reply.id),
                        did=notif.uri,
                    )
                )

    @loop(seconds=10)
    async def post_queue(self):
        await bluesky.post()

def setup(bot: Bot):
    if ATPROTO_EMAIL is not None and ATPROTO_PASSWORD is not None:
        bot.add_cog(Bluesky(bot))
    else:
        obsidian_logger.info("skipping bluesky stuff")
