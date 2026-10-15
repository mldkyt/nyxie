# Meow counter

from discord import Bot, Cog, message_command, ApplicationContext, Message, DeletedReferencedMessage
from sqlalchemy import insert

from constants import GUILD, OWNER
from database import engine, qna_messages


class QnA(Cog):
    def __init__(self, bot: Bot) -> None:
        super().__init__()
        self.bot = bot

    @message_command(guild_ids=[int(GUILD)])
    async def qna(self, ctx: ApplicationContext, message: Message):
        if ctx.user.id != int(OWNER):
            await ctx.respond("Only owner of the bot can run this command.", ephemeral=True)
            return

        if (
            message.reference is None or
            isinstance(message.reference, DeletedReferencedMessage) or
            message.reference.resolved is None or
            isinstance(message.reference.resolved, DeletedReferencedMessage)
        ):
            await ctx.respond("This answer is not a reply to a question", ephemeral=True)
            return

        with engine.begin() as c:
            c.execute(
                insert(qna_messages)
                .values(
                    message_1_id=str(message.id),
                    message_2_id=str(message.reference.resolved.id),
                    question=str(message.reference.resolved.content),
                    answer=str(message.content),
                )
            )

        await ctx.respond("Added QnA question successfully", ephemeral=True)


def setup(bot: Bot):
    bot.add_cog(QnA(bot))