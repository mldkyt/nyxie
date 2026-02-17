import datetime

from discord import Bot, Cog, Color, Embed, EmbedFooter, Member
from discord.ext.tasks import loop
from discord.ui import (
    ActionRow,
    Button,
    Container,
    DesignerView,
    Separator,
    TextDisplay,
)

from constants import CHANNEL_GENERAL, CHANNEL_ROLES, GUILD
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
            obsidian_logger.warning(
                "The guild %s (%s) is not ours!", guild.name, str(guild.id)
            )
            return

        roles = guild.get_channel(int(CHANNEL_ROLES))
        if roles is None:
            obsidian_logger.error(
                "null roles channel: %s not a valid channel id in %s",
                CHANNEL_ROLES,
                GUILD,
            )
            return

        com = Container(
            TextDisplay("# New Member!"),
            TextDisplay(f"Welcome {member.mention} to this server!"),
            Separator(),
            ActionRow(Button(url=roles.jump_url, label="Pick some roles!")),
        )

        self.first_queue.append((member.id, com, datetime.datetime.now()))

    @Cog.listener()
    async def on_member_remove(self, member: Member):
        self.first_queue = [i for i in self.first_queue if i[0] != member.id]
        self.posts = [
            i
            for i in self.posts
            if (datetime.datetime.now() - i[2]).total_seconds() < 600
        ]

        a = [i for i in self.posts if i[1] == member.id]
        if len(a) == 1:
            channel = member.guild.get_channel(int(CHANNEL_GENERAL))
            message = await channel.fetch_message(a[0][0])
            await message.delete()

    async def handle_first_queue(self):
        if len(self.first_queue) == 0:
            return

        a = self.first_queue.pop(0)

        if (datetime.datetime.now() - a[2]).total_seconds() < 10:
            self.first_queue.append(a)
            return

        guild = self.bot.get_guild(int(GUILD))
        general = guild.get_channel(int(CHANNEL_GENERAL))

        b = await general.send(view=DesignerView(a[1]))

        self.posts.append((b.id, a[0], datetime.datetime.now()))

    @loop(seconds=1)
    async def handle_queue(self):
        await self.handle_first_queue()


def setup(bot: Bot):
    bot.add_cog(WelcomeNewUsers(bot))
