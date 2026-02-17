from asyncio import gather
from datetime import datetime
from random import choice, randint

from aiohttp import ClientSession
from discord import Bot, ButtonStyle, Cog, Guild, MediaGalleryItem, TextChannel
from discord.ext.tasks import loop
from discord.types.components import TextDisplayComponent
from discord.ui import (
    ActionRow,
    Button,
    Container,
    DesignerView,
    MediaGallery,
    Separator,
    TextDisplay,
)

from constants import (
    CHANNEL_MEOW,
    CHANNEL_YAOI,
    CHANNEL_YURI,
    FEDI_INSTANCE,
    GUILD,
    VERSION,
)
from logger import obsidian_logger
from util.sharkey import sharkey_cache

DEBUG = False


async def post_yuri(bot: Bot):
    guild = bot.get_guild(int(GUILD))
    if not isinstance(guild, Guild):
        obsidian_logger.warning("Guild not found")
        return

    chan = guild.get_channel(int(CHANNEL_YURI))
    if not isinstance(chan, TextChannel):
        obsidian_logger.warning("Yuri channel not found :(")
        return

    yuri = await sharkey_cache.get_yuribot_post()
    if yuri is None:
        obsidian_logger.warning("No yuri :(")
        return  # :(

    component = Container(
        TextDisplay("# Daily Yuri"),
        Separator(),
        MediaGallery(MediaGalleryItem(url=yuri["files"][0]["url"])),
        TextDisplay(f"-# Tags: {yuri['files'][0]['comment']}"),
        Separator(),
        ActionRow(
            Button(
                label="Open yuri on fedi",
                style=ButtonStyle.url,
                url=f"https://{FEDI_INSTANCE}/notes/{yuri['id']}",
            )
        ),
        TextDisplay(f"-# obsidian {VERSION}"),
    )

    await chan.send(view=DesignerView(component))


async def post_yaoi(bot: Bot):
    guild = bot.get_guild(int(GUILD))
    if not isinstance(guild, Guild):
        return
    chan = guild.get_channel(int(CHANNEL_YAOI))
    if not isinstance(chan, TextChannel):
        return

    yaoi = await sharkey_cache.get_yaoibot_post()
    if yaoi is None:
        return  # :(

    component = Container(
        TextDisplay("# Daily Yaoi"),
        Separator(),
        MediaGallery(MediaGalleryItem(url=yaoi["files"][0]["url"])),
        Separator(),
        ActionRow(
            Button(
                label="Open yaoi on fedi",
                style=ButtonStyle.url,
                url=f"https://{FEDI_INSTANCE}/notes/{yaoi['id']}",
            )
        ),
        TextDisplay(f"-# obsidian {VERSION}"),
    )

    await chan.send(view=DesignerView(component))


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
            await gather(post_yuri(self.bot), post_yaoi(self.bot), post_meow(self.bot))


def setup(bot: Bot):
    bot.add_cog(ChannelPosting(bot))
