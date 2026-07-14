import os.path

from discord import (
    ButtonStyle,
    ChannelType,
    DeletedReferencedMessage,
    Embed,
    Interaction,
    Message,
    TextChannel,
    Thread,
)
from discord.abc import GuildChannel
from discord.ui import Button, View, button
from flask import request, session
from markdown_it import MarkdownIt
from sqlalchemy import Connection, delete, insert, select, update

from database import (
    engine,
    web_authors_list,
    web_channels_list,
    web_messages_attachments_list,
    web_messages_list,
)
from logger import lunamon_logger


def _add_author(c: Connection, message: Message):
    username = message.author.name
    if message.author.bot:
        username = message.author.name + "#" + message.author.discriminator
    elif message.webhook_id is not None:
        username = None

    c.execute(
        insert(web_authors_list).values(
            id=message.author.id,
            author_name=message.author.display_name,
            author_pfp=message.author.display_avatar.url,
            author_username=username,
        )
    )


def _update_author(c: Connection, message: Message):
    username = message.author.name
    if message.author.bot:
        username = message.author.name + "#" + message.author.discriminator
    elif message.webhook_id is not None:
        username = None

    c.execute(
        update(web_authors_list)
        .where(web_authors_list.c.id == message.author.id)
        .values(
            author_name=message.author.display_name,
            author_pfp=message.author.display_avatar.url,
            author_username=username,
        )
    )


def _add_or_update_author(c: Connection, message: Message):
    if (
        c.execute(
            select(web_authors_list.c.id).where(
                web_authors_list.c.id == message.author.id
            )
        ).fetchone()
        is None
    ):
        _add_author(c, message)
    else:
        _update_author(c, message)


def _add_channel(c: Connection, channel: TextChannel | Thread):
    if (
        channel.type == ChannelType.public_thread
        or channel.type == ChannelType.private_thread
    ):
        c.execute(
            insert(web_channels_list).values(
                id=channel.id, name=channel.name, type="thread"
            )
        )
    else:
        c.execute(
            insert(web_channels_list).values(
                id=channel.id,
                name=channel.name,
                type="channel",
                position=channel.position,
                category=None if channel.category is None else channel.category.name,
            )
        )


def _update_channel(c: Connection, channel: TextChannel | Thread):
    if (
        channel.type == ChannelType.public_thread
        or channel.type == ChannelType.private_thread
    ):
        c.execute(
            update(web_channels_list)
            .where(web_channels_list.c.id == channel.id)
            .values(name=channel.name, type="thread")
        )
    else:
        c.execute(
            update(web_channels_list)
            .where(web_channels_list.c.id == channel.id)
            .values(
                name=channel.name,
                type="channel",
                position=channel.position,
                category=None if channel.category is None else channel.category.name,
            )
        )


def add_or_update_channel(c: Connection, channel: TextChannel | Thread):
    if (
        c.execute(
            select(web_channels_list.c.id).where(web_channels_list.c.id == channel.id)
        ).fetchone()
        is None
    ):
        _add_channel(c, channel)
    else:
        _update_channel(c, channel)


async def _add_or_update_thread(c: Connection, thread: Thread):
    if (
        c.execute(
            select(web_channels_list).where(web_channels_list.c.id == thread.id)
        ).fetchone()
        is None
    ):
        _add_channel(c, thread)
    else:
        _update_channel(c, thread)

    async for message in thread.history(limit=1000):
        if (
            c.execute(
                select(web_messages_list.c.id).where(
                    web_messages_list.c.id == message.id
                )
            ).fetchone()
            is None
        ):
            await _add_message(c, message)
        else:
            await _update_message(c, message)


async def _add_attachments(c: Connection, message: Message):
    existing_attachments = [
        i[0]
        for i in c.execute(
            select(web_messages_attachments_list.c.attachment_name).where(
                web_messages_attachments_list.c.message_id == message.id
            )
        ).fetchall()
    ]

    if len(existing_attachments) != len(message.attachments):
        for i in range(len(existing_attachments)):
            attachment = existing_attachments[i]
            if os.path.exists(f"data/attachments/{message.id}/{i}-{attachment}"):
                os.remove(f"data/attachments/{message.id}/{i}-{attachment}")

            c.execute(
                delete(web_messages_attachments_list).where(
                    (web_messages_attachments_list.c.attachment_name == attachment)
                    & (web_messages_attachments_list.c.message_id == message.id)
                )
            )

    for i in range(len(message.attachments)):
        attachment = message.attachments[i]
        if not os.path.exists("data/attachments"):
            os.mkdir("data/attachments")
        if not os.path.exists(f"data/attachments/{message.id}"):
            os.mkdir(f"data/attachments/{message.id}")

        if os.path.exists(f"data/attachments/{message.id}/{i}-{attachment.filename}"):
            continue

        with open(
            f"data/attachments/{message.id}/{i}-{attachment.filename}", "wb"
        ) as f:
            lunamon_logger.debug(
                "Saving attachment %s for message %s",
                attachment.filename,
                str(message.id),
            )
            await attachment.save(f)

        c.execute(
            insert(web_messages_attachments_list).values(
                message_id=message.id,
                attachment_name=attachment.filename,
                attachment_url=f"/discord/explore/attachments/{message.id}/{i}-{attachment.filename}",
            )
        )


def _embed_to_text(embed: Embed):
    output = "\n\n"

    output += f"""## [Embed] {embed.title}

{embed.description}

"""
    if embed.image is not None:
        output += f"**[Image URL]({embed.image.url})**"

    if embed.author is not None:
        output += f"**Author**: {embed.author.name} "
        if embed.author.url is not None:
            output += f"[URL]({embed.author.url}) "
        if embed.author.icon_url is not None:
            output += f"[Icon URL]({embed.author.icon_url}) "

        output += "\n\n"

    for field in embed.fields:
        output += f"- **{field.name}**: {field.value} \n"

    output += "\n"

    if embed.footer is not None:
        output += f"**Footer**: {embed.footer.text} "
        if embed.footer.icon_url is not None:
            output += f"[Icon URL]({embed.footer.icon_url}) "

        output += "\n\n"

    return output


def _get_reference_message(message: Message):
    if message.reference is None:
        return None
    if message.reference.resolved is None:
        return None
    if isinstance(message.reference.resolved, DeletedReferencedMessage):
        return None

    return message.reference.resolved.id


async def _add_message(c: Connection, message: Message):
    _add_or_update_author(c, message)
    add_or_update_channel(c, message.channel)
    reply_msg = _get_reference_message(message)
    if message.thread is not None:
        await _add_or_update_thread(c, message.thread)

    channel_id = message.channel.id
    if (
        message.channel.type in [ChannelType.public_thread, ChannelType.private_thread]
        and message.channel.starting_message is not None
    ):
        channel_id = message.channel.starting_message.id

    content = message.clean_content

    if len(message.embeds) > 0:
        for embed in message.embeds:
            content += _embed_to_text(embed)

    c.execute(
        insert(web_messages_list).values(
            id=message.id,
            content=content.strip(),
            author_id=message.author.id,
            channel_id=channel_id,
            reply_msg=reply_msg,
            created_at=message.created_at,
            pinned=1 if message.pinned else 0,
        )
    )

    await _add_attachments(c, message)


async def _update_message(c: Connection, message: Message):
    _add_or_update_author(c, message)
    add_or_update_channel(c, message.channel)
    reply_msg = _get_reference_message(message)
    if message.thread is not None:
        await _add_or_update_thread(c, message.thread)

    content = message.clean_content

    if len(message.embeds) > 0:
        for embed in message.embeds:
            content += _embed_to_text(embed)

    c.execute(
        update(web_messages_list)
        .where(web_messages_list.c.id == message.id)
        .values(
            content=content,
            reply_msg=reply_msg,
            created_at=message.created_at,
            pinned=1 if message.pinned else 0,
        )
    )

    await _add_attachments(c, message)


def unpin_all_messages(ch: GuildChannel | Thread):
    with engine.begin() as c:
        c.execute(
            update(web_messages_list)
            .values(pinned=0)
            .where(
                (web_messages_list.c.pinned == 1)
                & (web_messages_list.c.channel_id == ch.id)
            )
        )


async def add_message(message: Message):
    if message.channel is None:
        return
    if message.guild is None:
        return

    if message.is_system():
        return
    if message.channel.type == ChannelType.private:
        return
    perms = message.channel.permissions_for(message.guild.default_role)
    if not perms.read_messages or not perms.view_channel:
        return

    with engine.begin() as c:
        if (
            c.execute(
                select(web_messages_list.c.id).where(
                    web_messages_list.c.id == message.id
                )
            ).fetchone()
            is None
        ):
            await _add_message(c, message)
        else:
            await _update_message(c, message)


def remove_message(message: int):
    with engine.begin() as c:
        c.execute(delete(web_messages_list).where(web_messages_list.c.id == message))


def get_channels():
    with engine.begin() as c:
        channels = c.execute(
            select(
                web_channels_list.c.id,
                web_channels_list.c.name,
                web_channels_list.c.category,
            )
            .where(web_channels_list.c.type == "channel")
            .order_by(web_channels_list.c.position)
        ).fetchall()

    categories = {}

    for channel in channels:
        if channel[2] not in categories:
            categories[channel[2]] = []

        categories[channel[2]].append({"id": channel[0], "name": channel[1]})

    return categories


def _process_message(c: Connection, msg):
    md = MarkdownIt("commonmark", {"html": False, "break": True})
    md.enable(["replacements", "smartquotes", "linkify"])

    output = {
        "id": msg[0],
        "content": md.render(msg[1]),
        "author_name": msg[2],
        "author_pfp": msg[3],
        "username": msg[4],
        "created_at": msg[5].strftime("%Y/%m/%d %H:%M"),
        "channel_id": msg[6],
    }

    # Append thread information if any is found
    thread = c.execute(
        select(web_channels_list.c.id, web_channels_list.c.name).where(
            web_channels_list.c.id == msg[0]
        )
    ).fetchone()
    if thread is not None:
        output["thread"] = {"id": thread[0], "name": thread[1]}

    replies = c.execute(
        select(web_messages_list.c.id).where(web_messages_list.c.reply_msg == msg[0])
    ).fetchall()

    if len(replies) > 0:
        output["reply_ids"] = []
        for reply in range(len(replies)):
            output["reply_ids"].append({"number": reply + 1, "id": replies[reply][0]})

    attachments = c.execute(
        select(
            web_messages_attachments_list.c.attachment_name,
            web_messages_attachments_list.c.attachment_url,
        ).where(web_messages_attachments_list.c.message_id == msg[0])
    ).fetchall()

    if len(attachments) > 0:
        output["attachments"] = [
            {"name": attachment[0], "url": attachment[1]} for attachment in attachments
        ]

    if msg[7] is not None:
        output["reply_to"] = msg[7]

    if len(msg) == 9:
        output["recurse"] = msg[8]

    output["thread_available"] = "reply_to" in output or "reply_ids" in output

    return output


def _process_messages(c: Connection, messages):
    output_list = []
    for msg in messages:
        output_list.append(_process_message(c, msg))

    return output_list


def get_latest_messages(channel: int, show_more: bool = False):
    with engine.begin() as c:
        messages_db = c.execute(
            select(
                web_messages_list.c.id,
                web_messages_list.c.content,
                web_authors_list.c.author_name,
                web_authors_list.c.author_pfp,
                web_authors_list.c.author_username,
                web_messages_list.c.created_at,
                web_messages_list.c.channel_id,
                web_messages_list.c.reply_msg,
            )
            .where(web_messages_list.c.channel_id == channel)
            .join(
                web_authors_list, web_authors_list.c.id == web_messages_list.c.author_id
            )
            .where(web_authors_list.c.consent == 1)
            .order_by(web_messages_list.c.id.desc())
            .limit(100 if show_more else 10)
        ).fetchall()

        messages = reversed(_process_messages(c, messages_db))

    return messages


def get_pinned_messages(channel: int):
    with engine.begin() as c:
        messages_db = c.execute(
            select(
                web_messages_list.c.id,
                web_messages_list.c.content,
                web_authors_list.c.author_name,
                web_authors_list.c.author_pfp,
                web_authors_list.c.author_username,
                web_messages_list.c.created_at,
                web_messages_list.c.channel_id,
                web_messages_list.c.reply_msg,
            )
            .where(
                (web_messages_list.c.channel_id == channel)
                & (web_messages_list.c.pinned == 1)
            )
            .join(
                web_authors_list, web_authors_list.c.id == web_messages_list.c.author_id
            )
            .where(web_authors_list.c.consent == 1)
            .order_by(web_messages_list.c.id.desc())
        ).fetchall()

        messages = reversed(_process_messages(c, messages_db))

    return messages


def _get_messages_above(channel_id: int, message_id: int, show_more: bool):
    with engine.begin() as c:
        above_db = c.execute(
            select(
                web_messages_list.c.id,
                web_messages_list.c.content,
                web_authors_list.c.author_name,
                web_authors_list.c.author_pfp,
                web_authors_list.c.author_username,
                web_messages_list.c.created_at,
                web_messages_list.c.channel_id,
                web_messages_list.c.reply_msg,
            )
            .where(
                (web_messages_list.c.id < message_id)
                & (web_messages_list.c.channel_id == channel_id)
            )
            .join(
                web_authors_list, web_authors_list.c.id == web_messages_list.c.author_id
            )
            .where(web_authors_list.c.consent == 1)
            .order_by(web_messages_list.c.id.desc())
            .limit(25 if show_more else 5)
        ).fetchall()

        above = reversed(_process_messages(c, above_db))

    return above


def _get_messages_under(channel_id: int, message_id: int, show_more: bool) -> list:
    with engine.begin() as c:
        under_db = c.execute(
            select(
                web_messages_list.c.id,
                web_messages_list.c.content,
                web_authors_list.c.author_name,
                web_authors_list.c.author_pfp,
                web_authors_list.c.author_username,
                web_messages_list.c.created_at,
                web_messages_list.c.channel_id,
                web_messages_list.c.reply_msg,
            )
            .where(
                (web_messages_list.c.id > message_id)
                & (web_messages_list.c.channel_id == channel_id)
            )
            .join(
                web_authors_list, web_authors_list.c.id == web_messages_list.c.author_id
            )
            .where(web_authors_list.c.consent == 1)
            .order_by(web_messages_list.c.id.asc())
            .limit(25 if show_more else 5)
        ).fetchall()

        under = _process_messages(c, under_db)

    return under


def get_surrounding_messages(message_id: int, show_more: bool = False):
    with engine.begin() as c:
        target_db = c.execute(
            select(
                web_messages_list.c.id,
                web_messages_list.c.content,
                web_authors_list.c.author_name,
                web_authors_list.c.author_pfp,
                web_authors_list.c.author_username,
                web_messages_list.c.created_at,
                web_messages_list.c.channel_id,
                web_messages_list.c.reply_msg,
            )
            .join(
                web_authors_list, web_authors_list.c.id == web_messages_list.c.author_id
            )
            .where(web_authors_list.c.consent == 1)
            .where(web_messages_list.c.id == message_id)
        ).fetchone()
        if target_db is None:
            print("Target not found")
            return []

        target = _process_message(c, target_db)
        target["is_highlight"] = True

    response = [
        *_get_messages_above(target_db[6], message_id, show_more=show_more),
        target,
        *_get_messages_under(target_db[6], message_id, show_more=show_more),
    ]

    return response


def _replies(c: Connection, message_id: int, recurse: int = 0):
    if recurse == 10:
        return []

    output = []

    messages = c.execute(
        select(
            web_messages_list.c.id,
            web_messages_list.c.content,
            web_authors_list.c.author_name,
            web_authors_list.c.author_pfp,
            web_authors_list.c.author_username,
            web_messages_list.c.created_at,
            web_messages_list.c.channel_id,
            web_messages_list.c.reply_msg,
        )
        .join(web_authors_list, web_authors_list.c.id == web_messages_list.c.author_id)
        .where(
            (web_messages_list.c.reply_msg == message_id)
            & (web_authors_list.c.consent == 1)
        )
    ).fetchall()

    for message in messages:
        output.append([*message, recurse])
        output.extend(_replies(c, message[0], recurse + 1))

    return output


def get_reply_thread(message_id: int, recurse: int = 0):
    with engine.begin() as c:
        # First message
        first_msg = c.execute(
            select(web_messages_list.c.id, web_messages_list.c.reply_msg)
            .where(web_messages_list.c.id == message_id)
            .join(
                web_authors_list, web_authors_list.c.id == web_messages_list.c.author_id
            )
            .where(web_authors_list.c.consent == 1)
        ).fetchone()

        if first_msg is None:
            return []

        while first_msg is not None:
            next_msg = c.execute(
                select(web_messages_list.c.id, web_messages_list.c.reply_msg)
                .where(web_messages_list.c.id == first_msg[1])
                .join(
                    web_authors_list,
                    web_authors_list.c.id == web_messages_list.c.author_id,
                )
                .where(web_authors_list.c.consent == 1)
            ).fetchone()

            if next_msg is None:
                break

            first_msg = next_msg

        target_db = c.execute(
            select(
                web_messages_list.c.id,
                web_messages_list.c.content,
                web_authors_list.c.author_name,
                web_authors_list.c.author_pfp,
                web_authors_list.c.author_username,
                web_messages_list.c.created_at,
                web_messages_list.c.channel_id,
                web_messages_list.c.reply_msg,
            )
            .join(
                web_authors_list, web_authors_list.c.id == web_messages_list.c.author_id
            )
            .where(
                (web_messages_list.c.id == first_msg[0])
                & (web_authors_list.c.consent == 1)
            )
        ).fetchone()
        if target_db is None:
            print("Target not found")
            return []

        replies = _replies(c, first_msg[0], recurse=1)

        msgs_db = [[*target_db, 0], *replies]

        msgs = _process_messages(c, msgs_db)

    return msgs


def get_title_for_channel(id: int):
    prefix = ""
    if "m" in request.args:
        prefix = "Conversation in "
    elif "t" in request.args:
        prefix = "Thread in "

    with engine.begin() as c:
        channel = c.execute(
            select(web_channels_list.c.name, web_channels_list.c.type).where(
                web_channels_list.c.id == id
            )
        ).fetchone()

    if channel is None:
        return None

    if channel[1] == "thread":
        return f"{prefix}Thread: {channel[0]}"
    else:
        return f"{prefix}Channel #{channel[0]}"


THEMES = [
    {
        "name": "Pleroma Dark",
        "base": "dark",
        "accent": "#e2b188",
        "bg": "#0f161e",
        "highlight": "#151e2b",
        "text": "#b9b9ba",
    },
    {
        "name": "Pleroma Light",
        "base": "light",
        "accent": "#f55b1b",
        "bg": "#f2f6f9",
        "highlight": "#d6dfed",
        "text": "#304055",
    },
    {
        "name": "Catppuccin Mocha",
        "base": "dark",
        "bg": "#1e1e2e",
        "text": "#cdd6f4",
        "highlight": "#313244",
        "accent": "#cba6f7",
    },
    {
        "name": "Catppuccin Latte",
        "base": "light",
        "bg": "#eff1f5",
        "text": "#4c4f69",
        "highlight": "#ccd0da",
        "accent": "#8839ef",
    },
    {
        "name": "Monokai",
        "base": "dark",
        "text": "#FCFCFA",
        "accent": "#FF6188",
        "highlight": "#2e2b2e",
        "bg": "#221F22",
    },
    {
        "name": "Discord Onyx",
        "base": "dark",
        "text": "#fff",
        "bg": "#000000",
        "highlight": "#101011",
        "accent": "#5965F1",
    },
    {
        "name": "Discord flashbang",
        "base": "light",
        "text": "#000000",
        "bg": "#FBFBFB",
        "highlight": "#F3F3F4",
        "accent": "#5965F1",
    },
]


def pick_theme():
    if "theme" not in session:
        return THEMES[0]

    for theme in THEMES:
        if theme["name"] == session["theme"]:
            return theme

    return THEMES[0]


def themes():
    return [theme["name"] for theme in THEMES]


def process_preferences():
    if "more_msgs" in request.form and request.form["more_msgs"] == "on":
        session["more"] = "1"
    else:
        session["more"] = "0"

    if "theme" in request.form and request.form["theme"] in themes():
        session["theme"] = request.form["theme"]


def search_messages(query: str):
    with engine.begin() as c:
        messages_db = c.execute(
            select(
                web_messages_list.c.id,
                web_messages_list.c.content,
                web_authors_list.c.author_name,
                web_authors_list.c.author_pfp,
                web_authors_list.c.author_username,
                web_messages_list.c.created_at,
                web_messages_list.c.channel_id,
                web_messages_list.c.reply_msg,
            )
            .where(web_messages_list.c.content.icontains(query))
            .join(
                web_authors_list, web_authors_list.c.id == web_messages_list.c.author_id
            )
            .where(web_authors_list.c.consent == 1)
            .order_by(web_messages_list.c.id.desc())
            .limit(10)
        ).fetchall()

        messages = _process_messages(c, messages_db)

    return messages


class RemoveConsent(View):
    def __init__(self):
        super().__init__()

    @button(label="Remove consent", style=ButtonStyle.red)
    async def withdraw_consent(self, button: Button, interaction: Interaction):
        if not interaction.user:
            await interaction.respond(
                "Internal error: interaction.user is None", ephemeral=True
            )
            return

        with engine.begin() as c:
            consent_status = c.execute(
                select(web_authors_list.c.consent).where(
                    web_authors_list.c.id == interaction.user.id
                )
            ).fetchone()

            consented = consent_status[0] if consent_status is not None else False

            if consented:
                c.execute(
                    update(web_authors_list)
                    .values(consent=0)
                    .where(web_authors_list.c.id == interaction.user.id)
                )

        await interaction.respond("Consent withdrawn successfully", ephemeral=True)
        self.stop()
        self.disable_all_items()
        await interaction.edit(view=self)


class Consent(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Consent", style=ButtonStyle.green, custom_id="public_view_consent")
    async def consent(self, button: Button, interaction: Interaction):
        if not interaction.user:
            await interaction.respond(
                "Internal error: interaction.user is None", ephemeral=True
            )
            return

        with engine.begin() as c:
            consent_status = c.execute(
                select(web_authors_list.c.consent).where(
                    web_authors_list.c.id == interaction.user.id
                )
            ).fetchone()

            consented = consent_status[0] if consent_status is not None else False

            if not consented:
                c.execute(
                    update(web_authors_list)
                    .where(web_authors_list.c.id == interaction.user.id)
                    .values(consent=1)
                )

                await interaction.respond("Consented!", ephemeral=True)

            else:
                await interaction.respond(
                    "You have already consented. Do you want to withdraw consent?",
                    view=RemoveConsent(),
                    ephemeral=True,
                )
