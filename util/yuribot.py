import os

from mastodon import Mastodon


class YuriBot:
    def __init__(self):
        print("Yuribot initialized")
        self.mastodon_yuribot = Mastodon(access_token="data/yuribot_usercred.secret")
        self.me = self.mastodon_yuribot.me()

    def also_post_on_fedi(self, filename: str, source: str, cw: str):
        print("Posting yuri")
        yuri_media_id = self.mastodon_yuribot.media_post(filename)
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
