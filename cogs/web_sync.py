import datetime

from discord import Cog, Bot, Message, RawMessageUpdateEvent, RawMessageDeleteEvent, Thread, ChannelType
from discord.abc import GuildChannel
from sqlalchemy import delete, update

from constants import GUILD
from database import engine, web_channels_list, web_messages_list
from logger import lunamon_logger
from util.web_sync import add_message, remove_message, unpin_all_messages


class WebSync(Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        guild = self.bot.get_guild(int(GUILD))
        for channel in guild.text_channels:
            if channel.permissions_for(guild.default_role).read_messages:
                async for message in channel.history(limit=1000):
                    try:
                        await add_message(message)
                    except Exception:
                        lunamon_logger.exception("Failed to add message to web UI:")

    @Cog.listener()
    async def on_message(self, message: Message):
        try:
            await add_message(message)
        except Exception:
            lunamon_logger.exception("Error adding message:")

    @Cog.listener()
    async def on_raw_message_edit(self, payload: RawMessageUpdateEvent):
        if payload.guild_id is None:
            return
        if payload.channel_id is None:
            return

        try:
            guild = self.bot.get_guild(payload.guild_id)
            if guild is None:
                return
            channel = guild.get_channel(payload.channel_id)
            if channel is None:
                return
            if not channel.permissions_for(guild.me).read_messages:
                return
            message = payload.cached_message or await channel.fetch_message(payload.message_id)
            if message.is_system():
                return
            await add_message(message) # will update
        except Exception:
            lunamon_logger.exception("Error editing message:")

    @Cog.listener()
    async def on_raw_message_delete(self, payload: RawMessageDeleteEvent):
        try:
            remove_message(payload.message_id)
        except Exception:
            lunamon_logger.exception("Error deleting message:")

    @Cog.listener()
    async def on_guild_channel_create(self, channel: GuildChannel):
        try:
            async for message in channel.history(limit=1000):
                try:
                    await add_message(message)
                except Exception:
                    lunamon_logger.exception("Failed to add message to web UI:")
        except Exception:
            lunamon_logger.exception("Failed adding new channel:")

    @Cog.listener()
    async def on_guild_channel_delete(self, channel: GuildChannel):
        try:
            with engine.begin() as c:
                c.execute(
                    delete(web_channels_list)
                    .where(web_channels_list.c.id == channel.id)
                )
        except Exception:
            lunamon_logger.exception("Failed removing channel:")

    @Cog.listener()
    async def on_guild_channel_update(self, before: GuildChannel, after: GuildChannel):
        async for message in after.history(limit=1000):
            try:
                await add_message(message)
            except Exception:
                lunamon_logger.exception("Failed to add message to web UI:")

    @Cog.listener()
    async def on_guild_channel_pins_update(self, channel: GuildChannel | Thread, last_pin: datetime.datetime):
        if channel.type in [ChannelType.public_thread, ChannelType.private_thread]:
            return

        unpin_all_messages(channel)

        async for pinned in channel.pins():
            await add_message(pinned.message)


def setup(bot: Bot):
    bot.add_cog(WebSync(bot))
