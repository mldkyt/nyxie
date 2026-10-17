from datetime import datetime
from datetime import datetime
from random import choice, randint

from discord import (
    ApplicationContext,
    Bot,
    Cog,
    Guild,
    TextChannel,
    default_permissions,
    slash_command,
)
from discord.ext.tasks import loop

from constants import (
    CHANNEL_MEOW,
    GUILD,
)
from util.yuri_util import (
    respond_with_thing_to_approve,
)

DEBUG = False


def generate_meow():
    meow = choice(["meow", "nya", "mraow", "mwrmmwra"])

    if meow == "nya":
        return "ny" + randint(1, 8) * "a"
    elif meow == "mwrmmwra":
        meow = "mr"
        for i in range(randint(4, 12)):
            meow += choice(["a", "w", "r"])

        return meow

    return meow


async def post_meow(bot: Bot):
    guild = bot.get_guild(int(GUILD))
    if not isinstance(guild, Guild):
        return
    chan = guild.get_channel(int(CHANNEL_MEOW))
    if not isinstance(chan, TextChannel):
        return

    await chan.send(generate_meow() + " :3")


class ChannelPosting(Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        self.periodic_run.start()

    @loop(minutes=1)
    async def periodic_run(self):
        now = datetime.now()

        if (now.hour == 0 and now.minute == 0) or DEBUG:
            await post_meow(self.bot)

    @slash_command(name="approve_fedi_suggestions")
    @default_permissions(manage_guild=True)
    async def approve_fedi_suggestions(self, ctx: ApplicationContext):
        if not await respond_with_thing_to_approve(ctx.interaction):
            await ctx.respond("nothing to approve", ephemeral=True)


def setup(bot: Bot):
    bot.add_cog(ChannelPosting(bot))
