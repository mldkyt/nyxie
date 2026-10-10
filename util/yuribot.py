import os
from asyncio import sleep

from mastodon import Mastodon

from logger import nyxie_logger


class YuriBot:
    def __init__(self):
        print("Yuribot initialized")
        self.mastodon_yuribot = Mastodon(access_token="data/yuribot_usercred.secret")
        self.me = self.mastodon_yuribot.me()

    async def also_post_on_fedi(self, filename: str, source: str, cw: str):
        print("Posting yuri")
        yuri_media_id = None

        for i in range(3):
            try:
                yuri_media_id = self.mastodon_yuribot.media_post(filename)
                break
            except Exception as e:
                await sleep((i + 1) * 5000)

                if i == 2:
                    nyxie_logger.exception("3 attempts at uploading yuri failed")
                    return

        assert yuri_media_id is not None

        self.mastodon_yuribot.status_post(
            f"Yuri!\n[source]({source})\n#yuri",
            media_ids=[yuri_media_id],
            sensitive=len(cw.strip()) > 0,
            spoiler_text=cw.strip(),
            visibility="unlisted",
        )


yuribot = None
if os.path.exists("data/yuribot_usercred.secret"):
    yuribot = YuriBot()
