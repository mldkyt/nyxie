import atproto

from constants import ATPROTO_EMAIL, ATPROTO_PASSWORD
from logger import obsidian_logger


# TODO: Crosspost fedi posts
# Do not crosspost boosts, replies, quote posts, posts with a poll
# Shorten posts longer than 300 letters.
#
# TODO: Post new YouTube videos on fedi


class Bluesky:
    def __init__(self) -> None:
        self.account = atproto.AsyncClient()

    post_queue = []
    logged_in = False

    async def log_in(self):
        obsidian_logger.info("[Bluesky]Logging in")
        if ATPROTO_EMAIL is not None and ATPROTO_PASSWORD is not None:
            self.profile = await self.account.login(ATPROTO_EMAIL, ATPROTO_PASSWORD)
            obsidian_logger.info("[Bluesky]Logged in as %s", str(self.profile.handle))
            self.logged_in = True


bluesky = Bluesky()
