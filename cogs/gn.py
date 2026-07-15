import datetime
import json
import os
import random
import string

from discord import Bot, Cog, Message
from discord.ext import tasks
from python_ntfy import HttpAction, NtfyClient
from sqlalchemy import insert

from database import engine, gn
from logger import lunamon_logger

NTFY_URL = os.getenv("NTFY_URL")
NTFY_TOKEN = os.getenv("NTFY_TOKEN")
API_ENDPOINT = os.getenv("API_ENDPOINT", "https://mldchan.dev")


class GnNotification(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

        if not NTFY_URL or not NTFY_TOKEN:
            raise Exception("Missing environment variables")

        self.ntfy_client = NtfyClient(topic="lunamon", server=NTFY_URL, auth=NTFY_TOKEN)

    @Cog.listener()
    async def on_ready(self) -> None:
        lunamon_logger.info("Cog gn notification loaded")
        self.check.start()

    @tasks.loop(seconds=60)
    async def check(self):
        # Morning check
        now = datetime.datetime.now()
        if now.hour == 6 and now.minute == 0:
            token = "".join(random.choices(string.ascii_letters + string.digits, k=16))

            with engine.begin() as c:
                c.execute(
                    insert(gn).values(
                        auth_code=token,
                        type="morning",
                        expiry=datetime.datetime.now() + datetime.timedelta(hours=1),
                    )
                )

            self.ntfy_client.send(
                "Post a good morning reminder",
                "Morning",
                actions=[
                    HttpAction(
                        label="Post",
                        url=f"{API_ENDPOINT}/api/lunamon/gn",
                        body=json.dumps({"token": token}),
                        headers={"Content-Type": "application/json"},
                    )
                ],
            )

        # Evening check
        if now.hour == 20 and now.minute == 0:
            token = "".join(random.choices(string.ascii_letters + string.digits, k=16))

            with engine.begin() as c:
                c.execute(
                    insert(gn).values(
                        auth_code=token,
                        type="evening",
                        expiry=datetime.datetime.now() + datetime.timedelta(hours=1),
                    )
                )

            self.ntfy_client.send(
                "Post a good evening reminder",
                "Evening",
                actions=[
                    HttpAction(
                        label="Post",
                        url=f"{API_ENDPOINT}/api/lunamon/gn",
                        body=json.dumps({"token": token}),
                        headers={"Content-Type": "application/json"},
                    )
                ],
            )


def setup(bot: Bot):
    if not NTFY_URL or not NTFY_TOKEN:
        lunamon_logger.warning("Gn notifications are disabled due to missing config")
        return

    bot.add_cog(GnNotification(bot))
