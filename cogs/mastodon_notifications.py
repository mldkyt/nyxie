import html2text
from discord import Bot, Cog
from discord.ext.tasks import loop
from mastodon.Mastodon import Notification
from sentry_sdk import capture_exception
from sqlalchemy import Connection, insert, select

from cogs.channel_posting import yuribot
from database import (
    acknowledged_notifications,
    alt_text_suggestions,
    engine,
    yaoi_db,
    yuri_db,
)
from util.yaoibot import yaoibot


def get_raw_alt_text(content: str):
    alt_text = html2text.html2text(content).strip()
    while alt_text.startswith("[@"):  # Cursed way to remove mentions
        alt_text = " ".join(alt_text.split(" ")[1:])

    return alt_text


def get_yuri_source(c: Connection, post_id: str):
    if yuribot is None:
        raise ValueError("This is not supposed to happen")

    yuri_post = yuribot.mastodon_yuribot.status(post_id)
    link = (  # Cursed way to find source link
        html2text.html2text(yuri_post.content)
        .splitlines()[1]
        .split("(")[1]
        .strip()[:-1]
    )

    yuri = c.execute(select(yuri_db.c.id).where(yuri_db.c.source == link)).fetchone()
    if yuri is None:
        return None

    return yuri[0]


def get_yaoi_source(c: Connection, post_id: str):
    if yaoibot is None:
        raise ValueError("This is not supposed to happen")

    yaoi_post = yaoibot.mastodon_yaoibot.status(post_id)
    link = (  # Cursed way to find source link
        html2text.html2text(yaoi_post.content)
        .splitlines()[1]
        .split("(")[1]
        .strip()[:-1]
    )

    yaoi = c.execute(select(yaoi_db.c.id).where(yaoi_db.c.source == link)).fetchone()
    if yaoi is None:
        return None

    return yaoi[0]


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
                        alt_text = get_raw_alt_text(notification.status.content)
                        yuri = get_yuri_source(c, notification.status.in_reply_to_id)

                        if yuri is None:
                            continue

                        # Alt text suggestion
                        c.execute(
                            insert(alt_text_suggestions).values(
                                fid=yuri,
                                status_id=notification.status.in_reply_to_id,
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
        print("Running notifications for yaoibot")
        if yaoibot is None:
            return

        with engine.begin() as c:
            for notification in yaoibot.mastodon_yaoibot.notifications(
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
                    if notification.status.in_reply_to_account_id != yaoibot.me.id:
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
                        alt_text = get_raw_alt_text(notification.status.content)
                        yaoi = get_yaoi_source(c, notification.status.in_reply_to_id)

                        if yaoi is None:
                            continue

                        # Alt text suggestion
                        c.execute(
                            insert(alt_text_suggestions).values(
                                fid=yaoi,
                                status_id=notification.status.in_reply_to_id,
                                type="yaoi",
                                alt=alt_text,
                                acct=notification.account.acct,
                            )
                        )

                        # Notify user the suggestion was accepted
                        yaoibot.mastodon_yaoibot.status_post(
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


def setup(bot: Bot):
    bot.add_cog(MastodonNotifications(bot))
