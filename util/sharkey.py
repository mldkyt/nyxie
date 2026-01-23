import datetime
import random
from uuid import uuid4

import aiohttp

from constants import (
    FEDI_INSTANCE,
    FEDI_USER_ID,
    FEDI_YAOIBOT_ID,
    FEDI_YURIBOT_ID,
)
from logger import obsidian_logger


class SharkeyCache:
    def __init__(self) -> None:
        pass

    latest_lunya_posts = []
    latest_lunya_posts_update = datetime.datetime(day=1, month=1, year=2000)

    latest_yuribot_posts = []
    latest_yaoibot_posts = []

    async def get_latest_posts(self):
        if (
            datetime.datetime.now() - self.latest_lunya_posts_update
        ).total_seconds() < 600:
            return self.latest_lunya_posts

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://{FEDI_INSTANCE}/api/users/notes",
                json={"limit": 10, "userId": FEDI_USER_ID},
            ) as resp:
                if not resp.ok:
                    obsidian_logger.error(
                        "Failed to fetch latest posts. Status %s was unexpected.",
                        str(resp.status),
                    )
                    return []

                js = await resp.json()

                self.latest_lunya_posts = js
                self.latest_lunya_posts_update = datetime.datetime.now()

        return self.latest_lunya_posts

    async def fetch_yuribot_posts(self):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://{FEDI_INSTANCE}/api/users/notes",
                json={"userId": FEDI_YURIBOT_ID, "limit": 100, "withFiles": True},
            ) as req:
                if not req.ok:
                    return

                self.latest_yuribot_posts = await req.json()

    async def get_yuribot_post(self):
        if len(self.latest_yuribot_posts) == 0:
            await self.fetch_yuribot_posts()

        if len(self.latest_yuribot_posts) == 0:
            return None

        random_post = random.choice(self.latest_yuribot_posts)
        self.latest_yuribot_posts = [
            i for i in self.latest_yuribot_posts if i["id"] != random_post["id"]
        ]

        return random_post

    async def fetch_yaoibot_posts(self):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://{FEDI_INSTANCE}/api/users/notes",
                json={"userId": FEDI_YAOIBOT_ID, "limit": 100, "withFiles": True},
            ) as req:
                if not req.ok:
                    return

                self.latest_yaoibot_posts = await req.json()

    async def get_yaoibot_post(self):
        if len(self.latest_yaoibot_posts) == 0:
            await self.fetch_yaoibot_posts()

        if len(self.latest_yaoibot_posts) == 0:
            return None

        random_post = random.choice(self.latest_yaoibot_posts)
        self.latest_yaoibot_posts = [
            i for i in self.latest_yaoibot_posts if i["id"] != random_post["id"]
        ]

        return random_post


sharkey_cache = SharkeyCache()
