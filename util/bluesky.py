from asyncio import sleep

import atproto
from atproto_client.models.app.bsky.feed.post import ReplyRef, Record
from atproto_client.utils import TextBuilder
from discord import TextChannel, Embed, Color

from constants import ATPROTO_EMAIL, ATPROTO_PASSWORD
from logger import obsidian_logger


class Bluesky:
    def __init__(self) -> None:
        self.account = atproto.AsyncClient()

    post_queue = []
    logged_in = False
    log_channel = None

    async def log_in(self, channel: TextChannel):
        obsidian_logger.info("[Bluesky] Logging in try 1")
        self.log_channel = channel
        tries = 1
        if ATPROTO_EMAIL is not None and ATPROTO_PASSWORD is not None:
            while True:
                try:
                    self.profile = await self.account.login(ATPROTO_EMAIL, ATPROTO_PASSWORD)
                    obsidian_logger.info("[Bluesky]Logged in as %s", str(self.profile.handle))
                    self.logged_in = True

                    break
                except Exception as e:
                    obsidian_logger.exception("Error occured during login:")
                    embed = Embed(
                        title="An Error Occured during login",
                        color=Color.red(),
                        description=str(e)
                    )

                    await channel.send(embed=embed)
                    await sleep(10)
                    tries += 1
                    obsidian_logger.info("[Bluesky] Logging in try %d", tries)

    def queue(self, text: str | TextBuilder):
        obsidian_logger.info("Bluesky queue: adding post with text %s", text)
        data = {
            "mode": "post",
            "text": text
        }

        self.post_queue.append(data)

    def queue_video(self, text: str | TextBuilder, video, video_alt):
        obsidian_logger.info("Bluesky queue: adding post with text %s", text)
        data = {
            "mode": "post_video",
            "text": text,
            "video": {
                "video": video,
                "videoAlt": video_alt
            }
        }

        self.post_queue.append(data)

    def queue_images(self, text: str | TextBuilder, images, image_alts):
        obsidian_logger.info("Bluesky queue: adding post with text %s", text)
        data = {
            "mode": "post_image",
            "text": text,
            "image": {
                "images": images,
                "imagesAlts": image_alts
            }
        }

        self.post_queue.append(data)

    def queue_reply(self, text: str, reply_uri: str, reply_cid: str):
        obsidian_logger.info("Bluesky queue: adding reply %s with URI %s and CID %s", text, reply_uri, reply_cid)

        data = {
            "mode": "reply",
            "text": text,
            "reply": {
                "uri": reply_uri,
                "cid": reply_cid
            }
        }

        self.post_queue.append(data)

    def queue_repost(self, repost_uri: str, repost_cid: str):
        obsidian_logger.info("Bluesky queue: adding repost URI %s CID %s", repost_uri, repost_cid)

        data = {
            "mode": "repost",
            "repost": {
                "uri": repost_uri,
                "cid": repost_cid
            }
        }

        self.post_queue.append(data)

    async def post(self):
        if len(self.post_queue) == 0:
            return

        post = self.post_queue.pop(0)

        obsidian_logger.info("Bluesky posting queue: %d queued, running job %s right now", len(self.post_queue),
                             post["mode"])

        while True:
            try:
                if post["mode"] == "post":
                    await self.account.send_post(post["text"])
                elif post["mode"] == "post_video":
                    await self.account.send_video(post["text"], video=post["video"]["video"],
                                                  video_alt=post["video"]["videoAlt"])
                elif post["mode"] == "post_image":
                    await self.account.send_images(post["text"], images=post["image"]["images"],
                                                   image_alts=post["image"]["imagesAlts"])
                elif post["mode"] == "reply":
                    await self.account.send_post(
                        post["text"],
                        reply_to=ReplyRef.model_validate(
                            {
                                "parent": {
                                    "uri": post["reply"]["uri"],
                                    "cid": post["reply"]["cid"],
                                },
                                "root": {
                                    "uri": post["reply"]["uri"],
                                    "cid": post["reply"]["cid"],
                                },
                            }
                        ),
                    )
                elif post["mode"] == "repost":
                    await self.account.repost(uri=post["repost"]["uri"], cid=post["repost"]["cid"])
                else:
                    raise ValueError("invalid mode")

                break
            except Exception as e:
                self.post_queue.append(post)
                obsidian_logger.exception("Error occured during posting:")

                if self.log_channel is not None:
                    embed = Embed(
                        title="An Error Occured during posting",
                        color=Color.red(),
                        description=str(e)
                    )

                    await self.log_channel.send(embed=embed)

    async def notifications(self):
        obsidian_logger.debug("Bluesky notifs Checking...")
        notifs = await bluesky.account.app.bsky.notification.list_notifications(
            {"reasons": ["reply", "mention"]}
        )

        for notif in notifs.notifications:
            if notif.is_read:
                continue

            if notif.reason == "reply":
                if not isinstance(notif.record, Record):
                    obsidian_logger.debug("Bluesky notifs Skipping reply: Record is null")
                    return
                if not isinstance(notif.record.reply, ReplyRef):
                    obsidian_logger.debug("Bluesky notifs Skipping reply: Reply is null")
                    return

                yield notif

        obsidian_logger.debug("Bluesky notifs Setting replies read")
        await bluesky.account.app.bsky.notification.update_seen(
            {"seen_at": bluesky.account.get_current_time_iso()}
        )

        obsidian_logger.debug("Bluesky notifs OK")



bluesky = Bluesky()
