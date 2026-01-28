from discord import Cog, Member, Bot, Embed, Color, EmbedFooter

from constants import GUILD, CHANNEL_GENERAL, CHANNEL_ROLES
from logger import obsidian_logger


class WelcomeNewUsers(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        super().__init__()

    @Cog.listener()
    async def on_member_join(self, member: Member):
        guild = self.bot.get_guild(int(GUILD))
        if member.guild.id != guild.id:
            obsidian_logger.warning("The guild %s (%s) is not ours!", guild.name, str(guild.id))
            return

        general = guild.get_channel(int(CHANNEL_GENERAL))

        embed = Embed(
            title=f"Welcome {member.display_name} to the server!",
            description=f"Please make sure to pick roles in <#{CHANNEL_ROLES}>! :3",
            color=Color.green(),
            footer=EmbedFooter("sent by obsidian")
        )

        await general.send(
            member.mention,
            embed=embed
        )


def setup(bot: Bot):
    bot.add_cog(WelcomeNewUsers(bot))
