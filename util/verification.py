import datetime

from discord import (
    Button,
    ButtonStyle,
    Embed,
    EmbedField,
    Guild,
    InputTextStyle,
    Interaction,
    Member,
    TextChannel,
)
from discord.ui import InputText, Modal, View, button
from sqlalchemy import insert, select, delete

from constants import CHANNEL_GENERAL, CHANNEL_MODERATION, MEMBER_ROLE
from database import engine, verifications


class VerificationModeratorView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Approve", style=ButtonStyle.green, custom_id="verification:approve")
    async def approve(self, button, interaction: Interaction):
        assert isinstance(interaction.user, Member)
        assert interaction.guild is not None
        assert interaction.message is not None
        assert CHANNEL_GENERAL is not None
        assert MEMBER_ROLE is not None`

        if (
            not interaction.user.guild_permissions.manage_guild
            or not interaction.user.guild_permissions.administrator
        ):
            await interaction.respond(
                "No permission to approve this user.", ephemeral=True
            )
            return

        with engine.begin() as c:
            message = c.execute(
                select(verifications.c.member_id, verifications.c.id).where(
                    verifications.c.moderator_message_id == str(interaction.message.id)
                )
            ).fetchone()

        if message is None:
            await interaction.respond("Moderator message not found", ephemeral=True)
            return

        # Give out member role
        member_role_id = int(MEMBER_ROLE)
        member_role = interaction.guild.get_role(member_role_id)
        assert member_role is not None

        member = interaction.guild.get_member(message[0])
        assert member is not None
        await member.add_roles(member_role)

        # Send welcome message in general chat
        general_channel_id = int(CHANNEL_GENERAL)
        general_channel = interaction.guild.get_channel(general_channel_id)
        assert isinstance(general_channel, TextChannel)

        await general_channel.send(f"Welcome <@{message[0]}> to the server!")

        # Remove the reference and disable view
        with engine.begin() as c:
            c.execute(
                delete(verifications)
                .where(verifications.c.id == message[1])
            )

        self.disable_all_items()
        await interaction.edit(view=self)
        self.stop()


class VerificationView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Verify", style=ButtonStyle.green, custom_id="verification:start")
    async def start_verify(self, button, interaction: Interaction):
        await interaction.response.send_modal(VerificationModal())


class VerificationModal(Modal):
    def __init__(self):
        super().__init__(title="Verification")

        self.about_text = InputText(
            style=InputTextStyle.long,
            label="About You",
            placeholder="e.g. I am a programmer and content creator. I am a fan of mldkyt. I enjoy making silly things with computers.",
        )

        self.add_item(self.about_text)

    async def callback(self, interaction: Interaction):
        assert CHANNEL_MODERATION is not None
        assert interaction.guild is not None
        assert interaction.user is not None

        moderation_channel_id = int(CHANNEL_MODERATION)
        moderation_channel = interaction.guild.get_channel(moderation_channel_id)
        assert moderation_channel is not None
        assert isinstance(moderation_channel, TextChannel)

        embed = Embed(
            title="Member verification",
            description=self.about_text.value,
            fields=[
                EmbedField(
                    name="User",
                    value=f"{interaction.user.mention} ({interaction.user.name}, {interaction.user.id})",
                )
            ],
        )

        message = await moderation_channel.send(
            "Please verify the following user",
            embed=embed,
            view=VerificationModeratorView(),
        )

        with engine.begin() as c:
            c.execute(
                insert(verifications).values(
                    moderator_message_id=str(message.id),
                    member_id=str(interaction.user.id),
                )
            )

        await interaction.respond("Your verification is now pending.", ephemeral=True)


async def unverified_members(guild: Guild):
    member_role = await guild.fetch_role(int(MEMBER_ROLE))

    async for member in guild.fetch_members(limit=None):
        if member.bot:
            continue
        if (
            member.guild_permissions.manage_guild
            or member.guild_permissions.kick_members
            or member.guild_permissions.ban_members
            or member.guild_permissions.mute_members
        ):
            continue
        if member_role in member.roles:
            continue
        if member.joined_at is not None and (
            datetime.datetime.now(datetime.UTC) - member.joined_at
        ) < datetime.timedelta(days=7):
            continue

        yield member


class RejoinView(View):
    def __init__(self):
        super().__init__()

        self.add_item(
            Button(
                url="https://discord.gg/uTWjgy2E4v",
                label="Rejoin the server",
                style=ButtonStyle.url,
            )
        )
