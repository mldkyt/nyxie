from discord import Bot, Cog, Embed, Guild, PermissionOverwrite, TextChannel
from discord.ext.tasks import loop
from discord.ui import DesignerView
from sqlalchemy import delete, insert, select

from constants import GUILD
from database import dm_channels, engine
from logger import nyxie_logger
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
            e = RecursionError("Too many attempts to create a channel were performed")
            raise e

        # Check channel
        with engine.begin() as c:
            channel_id = c.execute(
                select(dm_channels.c.channel_id).where(
                    dm_channels.c.user_id == str(user_id)
                )
            ).fetchone()

        if channel_id is not None:
            try:
                channel = await self.guild.fetch_channel(channel_id[0])
                if channel is not None:
                    return channel
            except Exception as e:
                nyxie_logger.exception("Failed to fetch DM channel, will attempt with a new one")
                with engine.begin() as c:
                    c.execute(
                        delete(dm_channels).where(dm_channels.c.user_id == str(user_id))
                    )
                    return await self.ensure_channel(user_id, r=r + 1)

        try:
            user = await self.guild.fetch_member(user_id)
        except Exception as e:
            raise e

        # Create new channel
        channel = await self.guild.create_text_channel(
            f"dm-{user.name}",
            overwrites={
                user: PermissionOverwrite(view_channel=True, send_messages=True),
                self.guild.default_role: PermissionOverwrite(view_channel=False),
            },
        )
        await channel.send(
            "welcome to \"dm's\". your dm's are off so this is a replacement"
        )

        with engine.begin() as c:
            c.execute(
                insert(dm_channels).values(
                    user_id=str(user.id), channel_id=str(channel.id)
                )
            )

        return channel

    @loop(seconds=5)
    async def send_dms_out(self):
        message = dm_cache.get_message_to_send()
        while message is not None:
            try:
                user = await self.guild.fetch_member(message[0])
            except Exception as e:
                nyxie_logger.exception("Failed to fetch member")

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
                except Exception as e:
                    nyxie_logger.exception("Failed to ensure DM channel")

            message = dm_cache.get_message_to_send()


def setup(bot: Bot):
    bot.add_cog(DM(bot))
