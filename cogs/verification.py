from faulthandler import disable

from discord import (
    ApplicationContext,
    Bot,
    Cog,
    Color,
    Embed,
    HTTPException,
    Member,
    TextChannel,
    default_permissions,
    slash_command,
)
from discord.ext.pages import Paginator
from discord.ext.tasks import loop
from sentry_sdk import capture_exception
from sqlalchemy import delete, select

from constants import CHANNEL_MODERATION, CHANNEL_VERIFICATION, OWNER
from database import engine, verifications
from util.verification import (
    RejoinView,
    VerificationModeratorView,
    VerificationView,
    unverified_members,
)


class Verification(Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot
        self.kick_members: list[Member] = []
        self.dm_members: list[Member] = []

    @Cog.listener()
    async def on_ready(self):
        self.kick_member.start()
        self.dm_member.start()

        self.bot.add_view(VerificationView())
        self.bot.add_view(VerificationModeratorView())

    @slash_command()
    @default_permissions(administrator=True)
    async def list_unverified(self, ctx: ApplicationContext):
        """List unverified users"""
        if ctx.user.id != int(OWNER):
            await ctx.respond("This command is not available for you", ephemeral=True)
            return

        await ctx.defer(ephemeral=True)

        members: list[Member] = []
        async for member in unverified_members(ctx.guild):
            members.append(member)

        pages = []
        current_page = "# Members that are about to be kicked: \n\n"
        for member in members:
            current_page += f"- {member.display_name} ({member.name}, {member.id})\n"

            if len(current_page) > 1000:
                pages.append(current_page)
                current_page = "\n"

        if len(current_page) > 0:
            pages.append(current_page)

        paginator = Paginator(pages)
        await paginator.respond(ctx.interaction, ephemeral=True)

    @slash_command()
    @default_permissions(administrator=True)
    async def dm_unverified(self, ctx: ApplicationContext):
        """Kick unverified users"""
        if ctx.user.id != int(OWNER):
            await ctx.respond("This command is not available for you", ephemeral=True)
            return

        members: list[Member] = []
        async for member in unverified_members(ctx.guild):
            members.append(member)

        self.dm_members.extend(members)
        await ctx.respond(
            f"dming reminders to {len(members)} members queued", ephemeral=True
        )

    @slash_command()
    @default_permissions(administrator=True)
    async def kick_unverified(
        self,
        ctx: ApplicationContext,
        confirm: bool = False,
        i_really_want_to_kick_members: bool = False,
    ):
        """Kick unverified users"""
        if ctx.user.id != int(OWNER):
            await ctx.respond("This command is not available for you", ephemeral=True)
            return

        if not confirm or not i_really_want_to_kick_members:
            await ctx.respond("The action was not confirmed", ephemeral=True)
            return

        members: list[Member] = []
        async for member in unverified_members(ctx.guild):
            members.append(member)

        self.kick_members.extend(members)
        await ctx.respond(f"Kicking {len(members)} members queued", ephemeral=True)

    @slash_command()
    @default_permissions(administrator=True)
    async def send_verification_message(self, ctx: ApplicationContext):
        if ctx.user.id != int(OWNER):
            await ctx.respond("This command is not available for you", ephemeral=True)
            return

        await ctx.channel.send(
            "# Verification\n\nPlease click verify below and fill out the modal that pops up.\n\nVerification might take upwards of 2 days, depending on my availability.",
            view=VerificationView(),
        )
        await ctx.respond("Sent", ephemeral=True)

    @Cog.listener()
    async def on_member_join(self, member: Member):
        try:
            assert CHANNEL_VERIFICATION is not None
            channel_verification_id = int(CHANNEL_VERIFICATION)
            channel_verification = member.guild.get_channel(channel_verification_id)
            assert isinstance(channel_verification, TextChannel)
            message = await channel_verification.send(
                f"{member.mention} Please start verification here."
            )
            await message.delete(delay=5)
        except Exception as e:
            capture_exception(e)

    @Cog.listener()
    async def on_member_remove(self, member: Member):
        try:
            assert CHANNEL_MODERATION is not None

            with engine.begin() as c:
                message = c.execute(
                    select(
                        verifications.c.moderator_message_id, verifications.c.id
                    ).where(verifications.c.member_id == str(member.id))
                ).fetchone()

            if message is None:
                return

            # Disable buttons on the moderation message
            moderation_channel_id = int(CHANNEL_MODERATION)
            moderation_channel = member.guild.get_channel(moderation_channel_id)
            assert moderation_channel is not None
            assert isinstance(moderation_channel, TextChannel)

            moderator_message_id = int(message[0])
            moderator_message = await moderation_channel.fetch_message(
                moderator_message_id
            )

            await moderator_message.edit(view=VerificationModeratorView(disabled=True))

            with engine.begin() as c:
                c.execute(delete(verifications).where(verifications.c.id == message[1]))
        except Exception as e:
            capture_exception(e)

    @loop(seconds=5)
    async def kick_member(self):
        if len(self.kick_members) == 0:
            return

        try:
            kick_this_member = self.kick_members.pop()
            try:
                await kick_this_member.send(
                    embed=Embed(
                        title="Kicked",
                        description="You have been kicked from mldkyt's Discord server for not verifying in the specified time window.\n"
                        "\n"
                        "Don't worry! You can rejoin using the button below and verify again.",
                        color=Color.red(),
                    ),
                    view=RejoinView(),
                )
            except HTTPException:
                pass

            await kick_this_member.kick(reason="Not verified in time period")
        except Exception as e:
            capture_exception(e)

    @loop(seconds=5)
    async def dm_member(self):
        if len(self.kick_members) == 0:
            return

        try:
            dm_this_member = self.dm_members.pop()

            assert CHANNEL_VERIFICATION is not None
            channel_verification_id = int(CHANNEL_VERIFICATION)
            channel_verification = dm_this_member.guild.get_channel(
                channel_verification_id
            )
            assert isinstance(channel_verification, TextChannel)

            try:
                await dm_this_member.send(
                    f"this is your reminder to verify today in {channel_verification.guild.name}. you can start in {channel_verification.mention}"
                )
            except HTTPException:
                message = await channel_verification.send(
                    f"{dm_this_member.mention} reminder: please verify. members that fail to verify in time will get kicked."
                )
                await message.delete(delay=5)

        except Exception as e:
            capture_exception(e)


def setup(bot: Bot):
    bot.add_cog(Verification(bot))
