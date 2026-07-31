import datetime

from discord import (
    Bot,
    ChannelType,
    Cog,
    Color,
    Embed,
    Member,
    Message,
    RawMessageDeleteEvent,
    RawMessageUpdateEvent,
    Thread,
)
from discord.abc import GuildChannel
from sentry_sdk import capture_exception
from sqlalchemy import delete, update

from constants import GUILD, OWNER, MEMBER_ROLE
from database import engine, web_authors_list, web_channels_list
from util.web_sync import Consent, add_message, remove_message, unpin_all_messages


class WebSync(Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        guild = self.bot.get_guild(int(GUILD))
        await guild.fetch_roles()
        member_role = guild.get_role(int(MEMBER_ROLE)) or guild.default_role

        for channel in guild.text_channels:
            if channel.permissions_for(member_role).read_messages:
                async for message in channel.history(limit=1000):
                    try:
                        await add_message(message)
                    except Exception as e:
                        capture_exception(e)

        self.bot.add_view(Consent())

    @Cog.listener()
    async def on_message(self, message: Message):
        try:
            if (
                str(message.author.id) == OWNER
                and message.content == "lm!send_consent_msg"
            ):
                await message.channel.send(
                    embed=Embed(
                        title="Public Message View",
                        color=Color.green(),
                        description="This server implements a unique way to view messages outside of Discord without an account. [You can see it in action here](https://mldchan.dev/discord/explore). However, I want your consent to show messages on here. This helps non-Discord users find out what my community is like, and make things like frequently asked questions and project discussions more accessible.",
                    ),
                    view=Consent(),
                )

                await message.delete()
                return

            await add_message(message)

        except Exception as e:
            capture_exception(e)

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
            message = payload.cached_message or await channel.fetch_message(
                payload.message_id
            )
            if message.is_system():
                return
            await add_message(message)  # will update
        except Exception as e:
            capture_exception(e)

    @Cog.listener()
    async def on_member_remove(self, member: Member):
        with engine.begin() as c:
            c.execute(
                update(web_authors_list)
                .where(web_authors_list.c.id == member.id)
                .values(consent=0)
            )

    @Cog.listener()
    async def on_raw_message_delete(self, payload: RawMessageDeleteEvent):
        try:
            remove_message(payload.message_id)
        except Exception as e:
            capture_exception(e)

    @Cog.listener()
    async def on_guild_channel_create(self, channel: GuildChannel):
        try:
            async for message in channel.history(limit=1000):
                try:
                    await add_message(message)
                except Exception as e:
                    capture_exception(e)
        except Exception as e:
            capture_exception(e)

    @Cog.listener()
    async def on_guild_channel_delete(self, channel: GuildChannel):
        try:
            with engine.begin() as c:
                c.execute(
                    delete(web_channels_list).where(
                        web_channels_list.c.id == channel.id
                    )
                )
        except Exception as e:
            capture_exception(e)

    @Cog.listener()
    async def on_guild_channel_update(self, before: GuildChannel, after: GuildChannel):
        async for message in after.history(limit=1000):
            try:
                await add_message(message)
            except Exception as e:
                capture_exception(e)

    @Cog.listener()
    async def on_guild_channel_pins_update(
        self, channel: GuildChannel | Thread, last_pin: datetime.datetime
    ):
        if channel.type in [ChannelType.public_thread, ChannelType.private_thread]:
            return

        unpin_all_messages(channel)

        async for pinned in channel.pins():
            await add_message(pinned.message)


def setup(bot: Bot):
    bot.add_cog(WebSync(bot))
