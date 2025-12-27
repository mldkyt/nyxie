import logging

import discord
from discord import Bot, Guild, Interaction, Member, Message, TextChannel, VoiceChannel
from sqlalchemy import insert, select

from constants import CHANNEL_MODERATION
from database import engine, reports

ai_logger = logging.getLogger("ai")


class ReportMessageOptions(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def approve_ban_reason(self, interaction: discord.Interaction, logs_id: int):
        try:
            if not isinstance(interaction.guild, Guild):
                await interaction.respond(
                    "This is supposed to be only executed inside of guilds",
                    ephemeral=True,
                )
                return

            # existing_data = get_data("reporting/reports")
            # data = next((i for i in existing_data if i["logs_msg"] == logs_id), None)
            with engine.begin() as cur:
                data = cur.execute(
                    select(reports.c.rid).where(reports.c.lid == str(logs_id))
                ).fetchone()

            if data is None:
                return

            reporter = await interaction.guild.fetch_member(data[0])
            if reporter is None:
                return

            emb = discord.Embed(
                title="Report Status",
                description="You reported a message recently. The message has violated the rules of the server and action has been taken against the content. Thank you for keeping the community safe.",
                color=discord.Color.green(),
                footer=discord.EmbedFooter(text="Lunya's Ai 愛"),
            )

            await reporter.send(embed=emb)
        except Exception as e:
            ai_logger.exception("An error occurred:")

    async def reject_ban_reason(self, interaction: discord.Interaction, logs_id: int):
        try:
            if not isinstance(interaction.guild, Guild):
                await interaction.respond(
                    "This is supposed to be only executed inside of guilds",
                    ephemeral=True,
                )
                return

            # existing_data = get_data("reporting/reports")
            # data = next((i for i in existing_data if i["logs_msg"] == logs_id), None)
            with engine.begin() as cur:
                data = cur.execute(
                    select(reports.c.rid).where(reports.c.lid == str(logs_id))
                ).fetchone()

            if data is None:
                return

            reporter = await interaction.guild.fetch_member(data[0])
            if reporter is None:
                return

            emb = discord.Embed(
                title="Report Status",
                description="You reported a message recently. The message has not violated the rules of the server. Thank you for your concerns, it is better to report suspicious content rather than not reporting it at all.",
                color=discord.Color.red(),
                footer=discord.EmbedFooter(text="Lunya's Ai 愛"),
            )

            await reporter.send(embed=emb)
        except Exception as e:
            ai_logger.exception("An error occurred:")

    # Buttons to report author of message

    @discord.ui.button(
        label="Reject", style=discord.ButtonStyle.success, custom_id="reject_report"
    )
    async def reject_report(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        if not isinstance(interaction.message, Message):
            await interaction.respond(
                "This is supposed to be attached to a message",
                ephemeral=True,
            )
            return
        await self.reject_ban_reason(interaction, interaction.message.id)
        await interaction.respond("Rejected!", ephemeral=True)

    @discord.ui.button(
        label="Ban Message Author...",
        style=discord.ButtonStyle.red,
        custom_id="ban_message_author",
        row=2,
    )
    async def ban_message_author(self, button, interaction: Interaction):
        try:
            if not isinstance(interaction.message, Message):
                await interaction.respond(
                    "This is supposed to be attached to a message",
                    ephemeral=True,
                )
                return

            with engine.begin() as cur:
                data = cur.execute(
                    select(reports.c.aid, reports.c.reason).where(
                        reports.c.lid == str(interaction.message.id)
                    )
                ).fetchone()

            if data is None:
                await interaction.respond(
                    "The moderation message was not found.", ephemeral=True
                )
                return

            # Show ban command for the author
            await interaction.respond(
                f"`/ban user:{data[0]} reason:{data[1]}`",
                ephemeral=True,
            )
            await self.approve_ban_reason(interaction, interaction.message.id)
        except Exception as e:
            ai_logger.exception("An error occurred:")
            await interaction.respond(
                "An error occured. Report created successfully.", ephemeral=True
            )

    @discord.ui.button(
        label="Warn Message Author...",
        style=discord.ButtonStyle.red,
        custom_id="warn_message_author",
        row=2,
    )
    async def warn_message_author(self, button, interaction: Interaction):
        try:
            if not isinstance(interaction.message, Message):
                await interaction.respond(
                    "This is supposed to be attached to a message",
                    ephemeral=True,
                )
                return

            with engine.begin() as cur:
                data = cur.execute(
                    select(reports.c.aid, reports.c.reason).where(
                        reports.c.lid == str(interaction.message.id)
                    )
                ).fetchone()

            if data is None:
                await interaction.respond(
                    "The moderation message was not found.", ephemeral=True
                )
                return

            # Generate a warning command for the user

            await interaction.respond(
                f"`/warn add user:{data[0]} reason:{data[1]}`",
                ephemeral=True,
            )
            await self.approve_ban_reason(interaction, interaction.message.id)
        except Exception as e:
            ai_logger.exception("An error occurred:")
            await interaction.respond(
                "An error occured. Report created successfully.", ephemeral=True
            )

    @discord.ui.button(
        label="Kick Message Author",
        style=discord.ButtonStyle.red,
        custom_id="kick_message_author",
        row=2,
    )
    async def kick_message_author(self, button, interaction: Interaction):
        try:
            if not isinstance(interaction.message, Message):
                await interaction.respond(
                    "This is supposed to be attached to a message",
                    ephemeral=True,
                )
                return

            with engine.begin() as cur:
                data = cur.execute(
                    select(reports.c.aid, reports.c.reason).where(
                        reports.c.lid == str(interaction.message.id)
                    )
                ).fetchone()

            if data is None:
                await interaction.respond(
                    "The moderation message was not found.", ephemeral=True
                )
                return

            # Show kick for message author

            await interaction.respond(
                f"`/kick user:{data[0]} reason:{data[1]}`",
                ephemeral=True,
            )
            await self.approve_ban_reason(interaction, interaction.message.id)
        except Exception as e:
            ai_logger.exception("An error occurred:")
            await interaction.respond(
                "An error occured. Report created successfully.", ephemeral=True
            )

    @discord.ui.button(
        label="Timeout Message Author 24h",
        style=discord.ButtonStyle.red,
        custom_id="timeout_message_author_1",
        row=2,
    )
    async def timeout_message_author_24h(self, button, interaction: Interaction):
        try:
            if not isinstance(interaction.message, Message):
                await interaction.respond(
                    "This is supposed to be attached to a message",
                    ephemeral=True,
                )
                return

            with engine.begin() as cur:
                data = cur.execute(
                    select(reports.c.aid, reports.c.reason).where(
                        reports.c.lid == str(interaction.message.id)
                    )
                ).fetchone()

            if data is None:
                await interaction.respond(
                    "The moderation message was not found.", ephemeral=True
                )
                return

            # Timeout message author for 24 hours

            await interaction.respond(
                f"`/timeout user:{data[0]} reason:{data[1]} days:1`",
                ephemeral=True,
            )
            await self.approve_ban_reason(interaction, interaction.message.id)
        except Exception as e:
            ai_logger.exception("An error occurred:")
            await interaction.respond(
                "An error occured. Report created successfully.", ephemeral=True
            )

    @discord.ui.button(
        label="Timeout Message Author 7d",
        style=discord.ButtonStyle.red,
        custom_id="timeout_message_author_2",
        row=2,
    )
    async def timeout_message_author_7d(self, button, interaction: Interaction):
        try:
            if not isinstance(interaction.message, Message):
                await interaction.respond(
                    "This is supposed to be attached to a message",
                    ephemeral=True,
                )
                return

            with engine.begin() as cur:
                data = cur.execute(
                    select(reports.c.aid, reports.c.reason).where(
                        reports.c.lid == str(interaction.message.id)
                    )
                ).fetchone()

            if data is None:
                await interaction.respond(
                    "The moderation message was not found.", ephemeral=True
                )
                return

            # Timeout message author for 7 days

            await interaction.respond(
                f"`/timeout user:{data[0]} reason:{data[1]} days:7`",
                ephemeral=True,
            )
            await self.approve_ban_reason(interaction, interaction.message.id)
        except Exception as e:
            ai_logger.exception("An error occurred:")
            await interaction.respond(
                "An error occured. Report created successfully.", ephemeral=True
            )


class EnterReportDetailsDialog(discord.ui.Modal):
    def __init__(self, channel_id: int, message_id: int, author_id: int):
        super().__init__(title="Report a message")

        self.channel_id = channel_id
        self.message_id = message_id
        self.author_id = author_id

        self.report_reason_field = discord.ui.InputText(
            label="Reason",
            placeholder="This user is...",
            style=discord.InputTextStyle.paragraph,
            required=True,
            min_length=4,
            max_length=512,
        )
        self.add_item(self.report_reason_field)

    async def callback(self, interaction: Interaction):
        if not isinstance(interaction.guild, Guild):
            await interaction.respond(
                "This is supposed to be only executed inside of guilds", ephemeral=True
            )
            return

        if not isinstance(interaction.user, Member):
            await interaction.respond("Reporting DM's is not supported", ephemeral=True)
            return

        if not isinstance(CHANNEL_MODERATION, str):
            await interaction.respond(
                "The CHANNEL_MODERATION variable is not defined, please define it to use this feature\nIf you're a user, notify the admins",
                ephemeral=True,
            )
            return

        if not isinstance(self.report_reason_field.value, str):
            await interaction.respond(
                "Please fill out the report reason", ephemeral=True
            )
            return

        logs_channel = interaction.guild.get_channel(int(CHANNEL_MODERATION))
        if not isinstance(logs_channel, TextChannel):
            await interaction.respond(
                "Error: Unable to find logs channel.", ephemeral=True
            )
            return

        # Resolve message

        target_channel = interaction.guild.get_channel(self.channel_id)
        if not isinstance(target_channel, TextChannel) and not isinstance(
            target_channel, VoiceChannel
        ):
            await interaction.respond(
                "Error: Unable to find the channel", ephemeral=True
            )
            return

        target_message = await target_channel.fetch_message(self.message_id)
        if target_message is None:
            await interaction.respond(
                "Error: Unable to find the message", ephemeral=True
            )
            return

        # Create logs embed

        emb = discord.Embed(
            title="New Message Report!",
            color=discord.Color.red(),
            description=f"A message was reported by {interaction.user.mention} that reports user <@{self.author_id=}>.",
            fields=[
                discord.EmbedField(
                    name="Message",
                    value=f"[jump]({target_message.jump_url})",
                    inline=True,
                ),
                discord.EmbedField(
                    name="Reason", value=self.report_reason_field.value, inline=True
                ),
                discord.EmbedField(
                    name="Message Author", value=f"<@{self.author_id=}>", inline=True
                ),
                discord.EmbedField(
                    name="Report Author", value=interaction.user.mention, inline=True
                ),
            ],
        )

        # Send to logs

        logs_msg = await logs_channel.send(embed=emb, view=ReportMessageOptions())

        # Save data about this message

        with engine.begin() as cur:
            cur.execute(
                insert(reports).values(
                    cid=str(str(self.channel_id)),
                    mid=str(str(self.message_id)),
                    rid=str(str(interaction.user.id)),
                    aid=str(str(self.author_id)),
                    lid=str(str(logs_msg.id)),
                )
            )

        # Respond to the user

        await interaction.respond(
            "User was reported successfully! Thank you for keeping the community safe.\n"
            "If you want to receive a message when your report is processed by our admin team, make sure you have DM's enabled!",
            ephemeral=True,
        )


class MessageReporting(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(ReportMessageOptions())

    @discord.message_command(
        name="Report Message", description="Report this message to the moderators."
    )
    async def report_message(
        self, ctx: discord.ApplicationContext, message: discord.Message
    ):
        await ctx.response.send_modal(
            EnterReportDetailsDialog(message.channel.id, message.id, message.author.id)
        )


def setup(bot: Bot):
    bot.add_cog(MessageReporting(bot))
