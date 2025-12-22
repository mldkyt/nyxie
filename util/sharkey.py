import datetime
import random
from uuid import uuid4

import aiohttp

from constants import (
    FEDI_INSTANCE,
    FEDI_USER_ID,
    FEDI_YAOIBOT_ID,
    FEDI_YURIBOT_ID,
    ai_logger,
)


class SharkeyCache:
    def __init__(self) -> None:
        pass

    latest_lunya_posts = []
    latest_lunya_posts_update = datetime.datetime(day=1, month=1, year=2000)

    latest_yuribot_posts = []
    latest_yaoibot_posts = []

    post_queue = []

    async def get_latest_posts(self):
        if (
            datetime.datetime.now() - self.latest_lunya_posts_update
        ).total_seconds() < 21600:
            return self.latest_lunya_posts

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://{FEDI_INSTANCE}/api/users/notes",
                json={"limit": 10, "userId": FEDI_USER_ID},
            ) as resp:
                if not resp.ok:
                    ai_logger.error(
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

    def post(self, user_token: str, post_text: str):
        self.post_queue.append(
            {"id": uuid4(), "token": user_token, "post": post_text, "attempt": 0}
        )

    async def send_next_post(self):
        if len(self.post_queue) == 0:
            return

        post = self.post_queue[0]

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://{FEDI_INSTANCE}/api/notes/create",
                json={"text": post["post"]},
                headers={"Authorization": f"Bearer {post['token']}"},
            ) as req:
                self.post_queue = [
                    i for i in self.post_queue if i["id"] != post["id"]
                ]  # Remove job
                if not req.ok:
                    post["attempt"] += 1  # Increase attempts
                    self.post_queue.append(
                        post
                    )  # Attempt job again (this will attempt it later in case of multiple jobs)

    def get_job_stats(self):
        jobs = len(self.post_queue)
        delayed = len([i for i in self.post_queue if i["attempt"] > 0])

        return f"job queue: Sharkey, queued jobs={jobs}, delayed jobs={delayed}"


sharkey_cache = SharkeyCache()
