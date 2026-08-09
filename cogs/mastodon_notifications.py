from html.parser import HTMLParser

import html2text
from discord import Bot, Cog
from discord.ext.tasks import loop
from markdown_it import MarkdownIt
from mastodon.Mastodon import Notification
from sentry_sdk import capture_exception
from sqlalchemy import insert, select

from cogs.channel_posting import yuribot
from database import acknowledged_notifications, alt_text_suggestions, engine, yuri_db


class MastodonNotifications(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        self.acknowledge_yuri_notifications.start()
        self.acknowledge_yaoi_notifications.start()

    @loop(minutes=1)
    async def acknowledge_yuri_notifications(self):
        print("Running notifications for yuribot")
        if yuribot is None:
            return

        with engine.begin() as c:
            for notification in yuribot.mastodon_yuribot.notifications(
                types=["mention"]
            ):
                try:
                    if not isinstance(notification, Notification):
                        print("Notification is not notification")
                        continue
                    if notification.status is None:
                        continue
                    if notification.status.in_reply_to_id is None:
                        continue
                    if notification.status.in_reply_to_account_id != yuribot.me.id:
                        continue
                    # Read notification check
                    if (
                        c.execute(
                            select(acknowledged_notifications).where(
                                acknowledged_notifications.c.id == str(notification.id)
                            )
                        ).fetchone()
                        is not None
                    ):
                        continue

                    if notification.status.spoiler_text == "ALT":
                        # Find the alt text
                        alt_text = html2text.html2text(
                            notification.status.content
                        ).strip()
                        while alt_text.startswith(
                            "[@"
                        ):  # Cursed way to remove mentions
                            alt_text = " ".join(alt_text.split(" ")[1:])

                        # Find the yuri post source URL and the database entry
                        yuri_post = yuribot.mastodon_yuribot.status(
                            notification.status.in_reply_to_id
                        )
                        link = (  # Cursed way to find source link
                            html2text.html2text(yuri_post.content)
                            .splitlines()[1]
                            .split("(")[1]
                            .strip()[:-1]
                        )

                        yuri = c.execute(
                            select(yuri_db.c.id).where(yuri_db.c.source == link)
                        ).fetchone()
                        if yuri is None:
                            continue

                        # Alt text suggestion
                        c.execute(
                            insert(alt_text_suggestions).values(
                                fid=yuri[0],
                                status_id=yuri_post.id,
                                type="yuri",
                                alt=alt_text,
                                acct=notification.account.acct,
                            )
                        )

                        # Notify user the suggestion was accepted
                        yuribot.mastodon_yuribot.status_post(
                            f"@{notification.account.acct} Your alt text suggestion was accepted and is now waiting approval from mldkyt.",
                            in_reply_to_id=notification.status.id,
                            visibility="direct",
                        )

                        c.execute(
                            insert(acknowledged_notifications).values(
                                id=str(notification.id)
                            )
                        )

                    if notification.status.spoiler_text == "CW":
                        # TODO: CW
                        pass
                except Exception as e:
                    capture_exception(e)

    @loop(minutes=1)
    async def acknowledge_yaoi_notifications(self):
        # TODO: Do this for yaoi content too
        pass


def setup(bot: Bot):
    bot.add_cog(MastodonNotifications(bot))
