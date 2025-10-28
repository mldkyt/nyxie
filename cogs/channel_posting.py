from asyncio import gather
from datetime import datetime
from random import choice, randint

from aiohttp import ClientSession
from discord import Cog, Bot
from discord.ext.tasks import loop
from mastodon import Mastodon

from constants import GUILD, CHANNEL_YURI, FEDI_INSTANCE, CHANNEL_YAOI, CHANNEL_MEOW

DEBUG = False

mastodon = Mastodon(access_token='data/usercred', api_base_url=f'https://{FEDI_INSTANCE}')

async def post_yuri(bot: Bot):
    guild = bot.get_guild(int(GUILD))
    chan = guild.get_channel(int(CHANNEL_YURI))

    acct = mastodon.account_statuses('AzXuGODH6RxPt5iFjE', only_media=True)
    await chan.send(f'https://{FEDI_INSTANCE}/notice/{choice(acct).id}')


async def post_yaoi(bot: Bot):
    guild = bot.get_guild(int(GUILD))
    chan = guild.get_channel(int(CHANNEL_YAOI))

    acct = mastodon.account_statuses('AzdWSJWKCcaguRcvwG', only_media=True)
    await chan.send(f'https://{FEDI_INSTANCE}/notice/{choice(acct).id}')


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
    chan = guild.get_channel(int(CHANNEL_MEOW))

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
            await gather(
                post_yuri(self.bot),
                post_yaoi(self.bot),
                post_meow(self.bot)
            )

def setup(bot: Bot):
    bot.add_cog(ChannelPosting(bot))
