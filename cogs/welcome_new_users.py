import datetime

from discord import Cog, Member, Bot, Embed, Color, EmbedFooter
from discord.ext.tasks import loop

from constants import GUILD, CHANNEL_GENERAL, CHANNEL_ROLES
from logger import obsidian_logger


class WelcomeNewUsers(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        super().__init__()

    first_queue = []
    posts = []

    @Cog.listener()
    async def on_ready(self):
        self.handle_queue.start()

    @Cog.listener()
    async def on_member_join(self, member: Member):
        guild = self.bot.get_guild(int(GUILD))
        if member.guild.id != guild.id:
            obsidian_logger.warning("The guild %s (%s) is not ours!", guild.name, str(guild.id))
            return

        embed = Embed(
            title=f"Welcome {member.display_name} to the server!",
            description=f"Please make sure to pick roles in <#{CHANNEL_ROLES}>! :3",
            color=Color.green(),
            footer=EmbedFooter("sent by obsidian")
        )

        self.first_queue.append(
            (member.mention, member.id, embed, datetime.datetime.now())
        )

    @Cog.listener()
    async def on_member_remove(self, member: Member):
        self.first_queue = [i for i in self.first_queue if i[1] != member.id]
        self.posts = [i for i in self.posts if (datetime.datetime.now() - i[2]).total_seconds() < 600]

        a = [i for i in self.posts if i[1] == member.id]
        if len(a) == 1:
            channel = member.guild.get_channel(int(CHANNEL_GENERAL))
            message = await channel.fetch_message(a[0][0])
            await message.delete()

    async def handle_first_queue(self):
        if len(self.first_queue) == 0:
            return

        a = self.first_queue.pop(0)

        if (datetime.datetime.now() - a[3]).total_seconds() < 10:
            self.first_queue.append(a)
            return

        guild = self.bot.get_guild(int(GUILD))
        general = guild.get_channel(int(CHANNEL_GENERAL))

        b = await general.send(
            a[0],
            embed=a[2]
        )

        self.posts.append(
            (b.id, a[1], datetime.datetime.now())
        )

    @loop(seconds=1)
    async def handle_queue(self):
        await self.handle_first_queue()


def setup(bot: Bot):
    bot.add_cog(WelcomeNewUsers(bot))
