import datetime

from mastodon import Mastodon
from mastodon.return_types import Status

from logger import lunamon_logger


class AkkomaCache:
    def __init__(self) -> None:
        self.safelogin()

    def safelogin(self):
        try:
            self.client = Mastodon(
                client_id="data/pytooter_clientcred.secret",
                access_token="data/pytooter_usercred.secret",
            )

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


akkoma_cache = AkkomaCache()
