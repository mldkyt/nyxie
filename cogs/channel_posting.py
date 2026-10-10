from asyncio import gather
from datetime import datetime
from random import choice, randint

from discord import (
    ApplicationContext,
    Bot,
    Cog,
    Color,
    Embed,
    EmbedFooter,
    File,
    Guild,
    TextChannel,
    default_permissions,
    slash_command,
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
from logger import nyxie_logger
from util.yaoibot import yaoibot
from util.yuri_util import (
    get_some_yaoi,
    get_some_yuri,
    respond_with_thing_to_approve,
)
from util.yuribot import yuribot

DEBUG = False


async def post_yuri(bot: Bot):
    try:
        guild = bot.get_guild(int(GUILD))
        if not isinstance(guild, Guild):
            return

        chan = guild.get_channel(int(CHANNEL_YURI))
        if not isinstance(chan, TextChannel):
            return

        with engine.begin() as c:
            yuri_filename, yuri_source, cw, alt = get_some_yuri(c)

        if not yuri_filename:
            return
        if not cw:
            cw = ""

        if len(cw.strip()) == 0:
            embed = Embed(
                title="yuri 🖤",
                image=f"attachment://{yuri_filename.split('/')[-1]}",
                footer=EmbedFooter(text=f"nyxie {VERSION}"),
                description=f"[source]({yuri_source})",
                color=Color.nitro_pink(),
            )
        else:
            embed = Embed(
                title="yuri 🖤",
                footer=EmbedFooter(text=f"nyxie {VERSION}"),
                description=f"[source]({yuri_source})",
                color=Color.nitro_pink(),
            )

        await chan.send(
            embed=embed,
            file=File(yuri_filename, spoiler=len(cw.strip()) > 0, description=alt),
        )

        if yuribot is not None:
            await yuribot.also_post_on_fedi(yuri_filename, yuri_source, cw)
    except Exception as e:
        nyxie_logger.exception("Failed to post yuri")


async def post_yaoi(bot: Bot):
    try:
        guild = bot.get_guild(int(GUILD))
        if not isinstance(guild, Guild):
            return
        chan = guild.get_channel(int(CHANNEL_YAOI))
        if not isinstance(chan, TextChannel):
            return

        with engine.begin() as c:
            yaoi_filename, yaoi_source, cw, alt = get_some_yaoi(c)

        if not yaoi_filename:
            return

        if not cw:
            cw = ""

        if len(cw.strip()) == 0:
            embed = Embed(
                title="yaoi 🖤",
                image=f"attachment://{yaoi_filename.split('/')[-1]}",
                footer=EmbedFooter(text=f"nyxie {VERSION}"),
                description=f"[source]({yaoi_source})",
                color=Color.nitro_pink(),
            )
        else:
            embed = Embed(
                title="yaoi 🖤",
                description=f"[source]({yaoi_source})",
                footer=EmbedFooter(text=f"nyxie {VERSION}"),
                color=Color.nitro_pink(),
            )

        await chan.send(
            embed=embed,
            file=File(yaoi_filename, spoiler=len(cw.strip()) > 0, description=alt),
        )

        if yaoibot is not None:
            await yaoibot.also_post_on_fedi(yaoi_filename, yaoi_source, cw)
    except Exception as e:
        nyxie_logger.exception("Failed to post yaoi")


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
        if now.minute == 0 or DEBUG:
            await gather(post_yuri(self.bot), post_yaoi(self.bot))

    @slash_command(name="approve_fedi_suggestions")
    @default_permissions(manage_guild=True)
    async def approve_fedi_suggestions(self, ctx: ApplicationContext):
        if not await respond_with_thing_to_approve(ctx.interaction):
            await ctx.respond("nothing to approve", ephemeral=True)


def setup(bot: Bot):
    bot.add_cog(ChannelPosting(bot))
