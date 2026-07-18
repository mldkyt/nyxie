from asyncio import gather
from datetime import datetime
from random import choice, randint

from discord import (
    Bot,
    Cog,
    Color,
    Embed,
    EmbedFooter,
    File,
    Guild,
    TextChannel,
)
from discord.ext.tasks import loop

from constants import (
    CHANNEL_MEOW,
    CHANNEL_YAOI,
    CHANNEL_YURI,
    GUILD,
    VERSION,
)
from database import engine
from logger import lunamon_logger
from util.yuri_util import get_some_yaoi, get_some_yuri

DEBUG = False


async def post_yuri(bot: Bot):
    guild = bot.get_guild(int(GUILD))
    if not isinstance(guild, Guild):
        lunamon_logger.warning("Guild not found")
        return

    chan = guild.get_channel(int(CHANNEL_YURI))
    if not isinstance(chan, TextChannel):
        lunamon_logger.warning("Yuri channel not found :(")
        return

    with engine.begin() as c:
        yuri_filename, yuri_source = get_some_yuri(c)

    if not yuri_filename:
        lunamon_logger.warning("No yuri found")
        return

    embed = Embed(
        title="Daily yuri",
        image=f"attachment://{yuri_filename.split('/')[-1]}",
        footer=EmbedFooter(text=f"Lunamon {VERSION}"),
        description=f"[source]({yuri_source})",
        color=Color.nitro_pink(),
    )

    await chan.send(embed=embed, file=File(yuri_filename))


async def post_yaoi(bot: Bot):
    guild = bot.get_guild(int(GUILD))
    if not isinstance(guild, Guild):
        return
    chan = guild.get_channel(int(CHANNEL_YAOI))
    if not isinstance(chan, TextChannel):
        return

    with engine.begin() as c:
        yaoi_filename, yaoi_source = get_some_yaoi(c)

    if not yaoi_filename:
        lunamon_logger.warning("No yaoi found")
        return

    embed = Embed(
        title="Daily yaoi",
        image=f"attachment://{yaoi_filename.split('/')[-1]}",
        description=f"[source]({yaoi_source})",
        color=Color.nitro_pink(),
    )

    await chan.send(embed=embed, file=File(yaoi_filename))


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
        if (now.hour in [0, 4, 8, 12, 16, 20] and now.minute == 0) or DEBUG:
            await gather(post_yuri(self.bot), post_yaoi(self.bot))


def setup(bot: Bot):
    bot.add_cog(ChannelPosting(bot))
