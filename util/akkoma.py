import datetime
import random

from mastodon import Mastodon
from mastodon.return_types import Status

from constants import FEDI_YURIBOT_ID, FEDI_YAOIBOT_ID
from logger import lunamon_logger


class AkkomaCache:
    def __init__(self) -> None:
        self.safelogin()

    def safelogin(self):
        try:
            self.client = Mastodon(client_id="data/pytooter_clientcred.secret", access_token="data/pytooter_usercred.secret")

            self.user = self.client.me()
            
            self.logged_in = True
        except Exception:
            lunamon_logger.exception("[Akkoma] Safelogin failed")

    logged_in = False

    latest_lunya_posts = []
    latest_lunya_posts_update = datetime.datetime(day=1, month=1, year=2000)

    def get_latest_posts(self) -> list[Status]:
        if not self.logged_in:
            lunamon_logger.error("[Akkoma] Not logged in yet, cannot get_latest_posts")
            return []

        if (
            datetime.datetime.now() - self.latest_lunya_posts_update
        ).total_seconds() < 600:
            return self.latest_lunya_posts

        self.latest_lunya_posts = self.client.account_statuses(self.user)

        return self.latest_lunya_posts

    def get_yuribot_post(self) -> Status | None:
        if not self.logged_in:
            lunamon_logger.error("[Akkoma] Cannot fetch yuri :( not logged in...")
            return None

        if FEDI_YURIBOT_ID is None:
            return None

        posts = [i for i in self.client.account_statuses(FEDI_YURIBOT_ID, only_media=True, limit=100)]
        random_post = random.choice(posts)

        return random_post

    def get_yaoibot_post(self) -> Status | None:
        if not self.logged_in:
            lunamon_logger.error("[Akkoma] Cannot fetch yaoi :( not logged in...")
            return None

        if FEDI_YAOIBOT_ID is None:
            return None

        posts = [i for i in self.client.account_statuses(FEDI_YAOIBOT_ID, only_media=True, limit=100)]
        random_post = random.choice(posts)

        return random_post


akkoma_cache = AkkomaCache()
