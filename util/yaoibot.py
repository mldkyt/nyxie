import os

from mastodon import Mastodon


class YaoiBot:
    def __init__(self):
        print("Yaoibot initialized")
        self.mastodon_yaoibot = Mastodon(access_token="data/yaoibot_usercred.secret")
        self.me = self.mastodon_yaoibot.me()

    def also_post_on_fedi(self, filename: str, source: str, cw: str):
        print("Posting yaoi")
        yaoi_media_id = self.mastodon_yaoibot.media_post(filename)
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
