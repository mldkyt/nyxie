from discord import Cog, Bot, Embed, Guild, TextChannel, PermissionOverwrite
from discord.ext.tasks import loop
from discord.ui import DesignerView
from sqlalchemy import select, insert, delete

from constants import GUILD
from database import engine, dm_channels
from logger import lunamon_logger
from util.dm import dm_cache


class DM(Cog):
    guild: Guild = None

    def __init__(self, bot: Bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        self.send_dms_out.start()
        self.guild = self.bot.get_guild(int(GUILD))

    async def ensure_channel(self, user_id: int, r=0) -> TextChannel:
        if r > 3:
            lunamon_logger.error("Failed to ensure DM channel for %d", user_id)
            raise RecursionError("Too many attempts to create a channel were performed")

        # Check channel
        with engine.begin() as c:
            channel_id = c.execute(
                select(dm_channels.c.channel_id)
                .where(dm_channels.c.user_id == str(user_id))
            ).fetchone()

        if channel_id is not None:
            try:
                channel = await self.guild.fetch_channel(channel_id[0])
                if channel is not None:
                    return channel
            except Exception:
                with engine.begin() as c:
                    c.execute(
                        delete(
                            dm_channels
                        ).where(dm_channels.c.user_id == str(user_id))
                    )
                    return await self.ensure_channel(user_id, r=r + 1)

        try:
            user = await self.guild.fetch_member(user_id)
        except Exception as e:
            lunamon_logger.exception("An error occured")
            raise e

        if user is None:
            raise ValueError("User should be in the server")

        # Create new channel
        channel = await self.guild.create_text_channel(f"dm-{user.name}", overwrites={
            user: PermissionOverwrite(view_channel=True, send_messages=True),
            self.guild.default_role: PermissionOverwrite(view_channel=False)
        })
        await channel.send("Since your DM's are off, this is a channel that will be used as \"DM's\". Any message here will ping you")

        with engine.begin() as c:
            c.execute(
                insert(dm_channels)
                .values(user_id=str(user.id), channel_id=str(channel.id))
            )

        return channel

    @loop(seconds=5)
    async def send_dms_out(self):
        message = dm_cache.get_message_to_send()
        while message is not None:
            try:

                user = await self.guild.fetch_member(message[0])
                if user is None:
                    raise ValueError("User not found")
            except Exception:
                lunamon_logger.exception("Tried to DM user that doesn't exist!")
                continue

            try:
                if isinstance(message[1], DesignerView):
                    await user.send(view=message[1])
                elif isinstance(message[1], Embed):
                    await user.send(embed=message[1])
                else:
                    await user.send(message[1])
            except Exception:

                try:
                    channel = await self.ensure_channel(message[0])
                    await channel.send(f"{user.mention}, {message[1]}")
                except Exception:
                    lunamon_logger.exception("An error occured when DMing")

            message = dm_cache.get_message_to_send()


def setup(bot: Bot):
    bot.add_cog(DM(bot))
