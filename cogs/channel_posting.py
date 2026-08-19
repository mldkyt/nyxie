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
from sentry_sdk import capture_exception

from constants import (
    CHANNEL_MEOW,
    CHANNEL_YAOI,
    CHANNEL_YURI,
    GUILD,
    VERSION,
)
from database import engine
from util.yaoibot import yaoibot
from util.yuri_util import (
    get_some_yaoi,
    get_some_yuri,
    respond_with_next_non_alted_content,
    respond_with_next_yuri,
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
                title="Yuri :3",
                image=f"attachment://{yuri_filename.split('/')[-1]}",
                footer=EmbedFooter(text=f"mldmon {VERSION}"),
                description=f"[source]({yuri_source})",
                color=Color.nitro_pink(),
            )
        else:
            embed = Embed(
                title="Yuri :3",
                footer=EmbedFooter(text=f"mldmon {VERSION}"),
                description=f"[source]({yuri_source})",
                color=Color.nitro_pink(),
            )

        await chan.send(
            embed=embed,
            file=File(yuri_filename, spoiler=len(cw.strip()) > 0, description=alt),
        )

        if yuribot is not None:
            yuribot.also_post_on_fedi(yuri_filename, yuri_source, cw)
    except Exception as e:
        capture_exception(e)


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
                title="Yaoi :3",
                image=f"attachment://{yaoi_filename.split('/')[-1]}",
                description=f"[source]({yaoi_source})",
                color=Color.nitro_pink(),
            )
        else:
            embed = Embed(
                title="Yaoi :3",
                description=f"[source]({yaoi_source})",
                color=Color.nitro_pink(),
            )

        await chan.send(
            embed=embed,
            file=File(yaoi_filename, spoiler=len(cw.strip()) > 0, description=alt),
        )

        if yaoibot is not None:
            yaoibot.also_post_on_fedi(yaoi_filename, yaoi_source, cw)
    except Exception as e:
        capture_exception(e)


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

    @slash_command(name="approve_content")
    @default_permissions(manage_guild=True)
    async def manage_content(self, ctx: ApplicationContext, reapprove: bool = False):
        if not await respond_with_next_yuri(ctx.interaction, reapprove=reapprove):
            await ctx.respond("All done!", ephemeral=True)

    @slash_command(name="add_alt_texts_to_content")
    @default_permissions(manage_guild=True)
    async def add_alt_texts(self, ctx: ApplicationContext):
        if not await respond_with_next_non_alted_content(ctx.interaction):
            await ctx.respond("All done!", ephemeral=True)

    @slash_command(name="approve_fedi_suggestions")
    @default_permissions(manage_guild=True)
    async def approve_fedi_suggestions(self, ctx: ApplicationContext):
        if not await respond_with_thing_to_approve(ctx.interaction):
            await ctx.respond("Nothing to approve from fedi", ephemeral=True)


def setup(bot: Bot):
    bot.add_cog(ChannelPosting(bot))
