import os
from asyncio import sleep

from mastodon import Mastodon
from sentry_sdk import capture_exception


class YaoiBot:
    def __init__(self):
        print("Yaoibot initialized")
        self.mastodon_yaoibot = Mastodon(access_token="data/yaoibot_usercred.secret")
        self.me = self.mastodon_yaoibot.me()

    async def also_post_on_fedi(self, filename: str, source: str, cw: str):
        print("Posting yaoi")
        # yaoi_media_id = self.mastodon_yaoibot.media_post(filename)

        yaoi_media_id = None

        for i in range(3):
            try:
                yaoi_media_id = self.mastodon_yaoibot.media_post(filename)
                break
            except Exception as e:
                await sleep((i + 1) * 5000)

                if i == 2:
                    capture_exception(e)
                    return

        assert yaoi_media_id is not None

        self.mastodon_yaoibot.status_post(
            f"Yaoi!\n[source]({source})\n#yaoi",
            media_ids=[yaoi_media_id],
            sensitive=len(cw.strip()) > 0,
            spoiler_text=cw.strip(),
            visibility="unlisted",
        )


yaoibot = None
if os.path.exists("data/yaoibot_usercred.secret"):
    yaoibot = YaoiBot()
