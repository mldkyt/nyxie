from certifi import where
from discord import Message, TextChannel, Thread, ChannelType, Embed
from discord.abc import GuildChannel
from flask import request, session
from markdown_it import MarkdownIt
from sqlalchemy import select, Connection, insert, update, delete

from database import engine, web_messages_list, web_authors_list, web_channels_list, web_messages_attachments_list


def _add_author(c: Connection, message: Message):
    username = message.author.name
    if message.author.bot:
        username = message.author.name + "#" + message.author.discriminator
    elif message.webhook_id is not None:
        username = None

    c.execute(
        insert(web_authors_list)
        .values(id=message.author.id, author_name=message.author.display_name,
                author_pfp=message.author.display_avatar.url,
                author_username=username)
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
        .values(author_name=message.author.display_name, author_pfp=message.author.display_avatar.url,
                author_username=username)
    )


def _add_or_update_author(c: Connection, message: Message):
    if c.execute(
            select(web_authors_list.c.id)
                    .where(web_authors_list.c.id == message.author.id)
    ).fetchone() is None:
        _add_author(c, message)
    else:
        _update_author(c, message)


def _add_channel(c: Connection, channel: TextChannel | Thread):
    if channel.type == ChannelType.public_thread or channel.type == ChannelType.private_thread:
        c.execute(
            insert(web_channels_list)
            .values(id=channel.id, name=channel.name, type="thread")
        )
    else:
        c.execute(
            insert(web_channels_list)
            .values(id=channel.id, name=channel.name, type="channel", position=channel.position,
                    category=None if channel.category is None else channel.category.name)
        )


def _update_channel(c: Connection, channel: TextChannel | Thread):
    if channel.type == ChannelType.public_thread or channel.type == ChannelType.private_thread:
        c.execute(
            update(web_channels_list)
            .where(web_channels_list.c.id == channel.id)
            .values(name=channel.name, type="thread")
        )
    else:
        c.execute(
            update(web_channels_list)
            .where(web_channels_list.c.id == channel.id)
            .values(name=channel.name, type="channel", position=channel.position,
                    category=None if channel.category is None else channel.category.name)
        )


def add_or_update_channel(c: Connection, channel: TextChannel | Thread):
    if c.execute(
            select(web_channels_list.c.id)
                    .where(web_channels_list.c.id == channel.id)
    ).fetchone() is None:
        _add_channel(c, channel)
    else:
        _update_channel(c, channel)


async def _add_or_update_thread(c: Connection, thread: Thread):
    if c.execute(
            select(web_channels_list)
                    .where(web_channels_list.c.id == thread.id)
    ).fetchone() is None:
        _add_channel(c, thread)
    else:
        _update_channel(c, thread)

    async for message in thread.history(limit=1000):
        if c.execute(
                select(web_messages_list.c.id)
                        .where(web_messages_list.c.id == message.id)
        ).fetchone() is None:
            await _add_message(c, message)
        else:
            await _update_message(c, message)

def _add_attachments(c: Connection, message: Message):
    for attachment in message.attachments:
        c.execute(
            insert(web_messages_attachments_list)
            .values(message_id=message.id, attachment_name=attachment.filename, attachment_url=attachment.url)
        )


async def _resolve_and_add_reply(c: Connection, msg: Message) -> int | None:
    if msg.reference is not None and msg.reference.resolved is not None:
        try:
            if c.execute(
                    select(web_messages_list.c.id)
                            .where(web_messages_list.c.id == msg.reference.message_id)
            ).fetchone() is None:
                await _add_message(c, msg.reference.resolved)
            else:
                await _update_message(c, msg.reference.resolved)
            return msg.reference.message_id
        except Exception:
            pass

    return None

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

async def _add_message(c: Connection, message: Message):
    _add_or_update_author(c, message)
    add_or_update_channel(c, message.channel)
    reply_msg = await _resolve_and_add_reply(c, message)
    if message.thread is not None:
        await _add_or_update_thread(c, message.thread)

    channel_id = message.channel.id
    if message.channel.type in [ChannelType.public_thread,
                                ChannelType.private_thread] and message.channel.starting_message is not None:
        channel_id = message.channel.starting_message.id

    content = message.clean_content

    if len(message.embeds) > 0:
        for embed in message.embeds:
            content += _embed_to_text(embed)

    c.execute(
        insert(web_messages_list)
        .values(id=message.id, content=content.strip(),
                author_id=message.author.id, channel_id=channel_id,
                reply_msg=reply_msg, created_at=message.created_at,
                pinned=1 if message.pinned else 0)
    )

    _add_attachments(c, message)

async def _update_message(c: Connection, message: Message):
    _add_or_update_author(c, message)
    add_or_update_channel(c, message.channel)
    reply_msg = await _resolve_and_add_reply(c, message)
    if message.thread is not None:
        await _add_or_update_thread(c, message.thread)

    content = message.clean_content

    if len(message.embeds) > 0:
        for embed in message.embeds:
            content += _embed_to_text(embed)

    c.execute(
        update(web_messages_list)
        .where(web_messages_list.c.id == message.id)
        .values(content=content, reply_msg=reply_msg, created_at=message.created_at,
                pinned=1 if message.pinned else 0)
    )

def unpin_all_messages(ch: GuildChannel | Thread):
    with engine.begin() as c:
        c.execute(
            update(web_messages_list)
            .values(pinned=0)
            .where((web_messages_list.c.pinned == 1) & (web_messages_list.c.channel_id == ch.id))
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
        if c.execute(
                select(web_messages_list.c.id)
                        .where(web_messages_list.c.id == message.id)
        ).fetchone() is None:
            await _add_message(c, message)
        else:
            await _update_message(c, message)

def remove_message(message: int):
    with engine.begin() as c:
        c.execute(
            delete(web_messages_list)
            .where(web_messages_list.c.id == message)
        )

def get_channels():
    with engine.begin() as c:
        channels = c.execute(
            select(web_channels_list.c.id, web_channels_list.c.name, web_channels_list.c.category)
            .where(web_channels_list.c.type == "channel")
            .order_by(web_channels_list.c.position)
        ).fetchall()

    categories = {}

    for channel in channels:
        if channel[2] not in categories:
            categories[channel[2]] = []

        categories[channel[2]].append({
            "id": channel[0],
            "name": channel[1]
        })

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
        "channel_id": msg[6]
    }

    # Append thread information if any is found
    thread = c.execute(
        select(web_channels_list.c.id, web_channels_list.c.name)
        .where(web_channels_list.c.id == msg[0])
    ).fetchone()
    if thread is not None:
        output["thread"] = {
            "id": thread[0],
            "name": thread[1]
        }

    replies = c.execute(
        select(web_messages_list.c.id)
        .where(web_messages_list.c.reply_msg == msg[0])
    ).fetchall()

    if len(replies) > 0:
        output["reply_ids"] = []
        for reply in range(len(replies)):
            output["reply_ids"].append({
                "number": reply + 1,
                "id": replies[reply][0]
            })

    attachments = c.execute(
        select(web_messages_attachments_list.c.attachment_name, web_messages_attachments_list.c.attachment_url)
        .where(web_messages_attachments_list.c.message_id == msg[0])
    ).fetchall()

    if len(attachments) > 0:
        output["attachments"] = [{
            "name": attachment[0],
            "url": attachment[1]
        } for attachment in attachments]


    if msg[7] is not None:
        output["reply_to"] = msg[7]

    output["thread_available"] = "reply_to" in output or "reply_ids" in output

    return output


def _process_messages(c: Connection, messages):
    output_list = []
    for msg in messages:
        output_list.append(
            _process_message(c, msg)
        )

    return output_list


def get_latest_messages(channel: int, show_more: bool = False):
    with engine.begin() as c:
        messages_db = c.execute(
            select(web_messages_list.c.id, web_messages_list.c.content, web_authors_list.c.author_name,
                   web_authors_list.c.author_pfp, web_authors_list.c.author_username, web_messages_list.c.created_at,
                   web_messages_list.c.channel_id, web_messages_list.c.reply_msg)
            .where(web_messages_list.c.channel_id == channel)
            .join(web_authors_list, web_authors_list.c.id == web_messages_list.c.author_id)
            .order_by(web_messages_list.c.id.desc())
            .limit(100 if show_more else 10)
        ).fetchall()

        messages = reversed(_process_messages(c, messages_db))

    return messages


def get_pinned_messages(channel: int):
    with engine.begin() as c:
        messages_db = c.execute(
            select(web_messages_list.c.id, web_messages_list.c.content, web_authors_list.c.author_name,
                   web_authors_list.c.author_pfp, web_authors_list.c.author_username, web_messages_list.c.created_at,
                   web_messages_list.c.channel_id, web_messages_list.c.reply_msg)
            .where((web_messages_list.c.channel_id == channel) & (web_messages_list.c.pinned == 1))
            .join(web_authors_list, web_authors_list.c.id == web_messages_list.c.author_id)
            .order_by(web_messages_list.c.id.desc())
        ).fetchall()

        messages = reversed(_process_messages(c, messages_db))

    return messages


def _get_messages_above(channel_id: int, message_id: int, show_more: bool):
    with engine.begin() as c:
        above_db = c.execute(
            select(web_messages_list.c.id, web_messages_list.c.content, web_authors_list.c.author_name,
                   web_authors_list.c.author_pfp, web_authors_list.c.author_username, web_messages_list.c.created_at,
                   web_messages_list.c.channel_id, web_messages_list.c.reply_msg)
            .where((web_messages_list.c.id < message_id) & (web_messages_list.c.channel_id == channel_id))
            .join(web_authors_list, web_authors_list.c.id == web_messages_list.c.author_id)
            .order_by(web_messages_list.c.id.desc())
            .limit(25 if show_more else 5)
        ).fetchall()

        above = reversed(_process_messages(c, above_db))

    return above


def _get_messages_under(channel_id: int, message_id: int, show_more: bool) -> list:
    with engine.begin() as c:
        under_db = c.execute(
            select(web_messages_list.c.id, web_messages_list.c.content, web_authors_list.c.author_name,
                   web_authors_list.c.author_pfp, web_authors_list.c.author_username, web_messages_list.c.created_at,
                   web_messages_list.c.channel_id, web_messages_list.c.reply_msg)
            .where((web_messages_list.c.id > message_id) & (web_messages_list.c.channel_id == channel_id))
            .join(web_authors_list, web_authors_list.c.id == web_messages_list.c.author_id)
            .order_by(web_messages_list.c.id.asc())
            .limit(25 if show_more else 5)
        ).fetchall()

        under = _process_messages(c, under_db)

    return under


def get_surrounding_messages(message_id: int, show_more: bool = False):
    with engine.begin() as c:
        target_db = c.execute(
            select(web_messages_list.c.id, web_messages_list.c.content, web_authors_list.c.author_name,
                   web_authors_list.c.author_pfp, web_authors_list.c.author_username, web_messages_list.c.created_at,
                   web_messages_list.c.channel_id, web_messages_list.c.reply_msg)
            .join(web_authors_list, web_authors_list.c.id == web_messages_list.c.author_id)
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
        *_get_messages_under(target_db[6], message_id, show_more=show_more)
    ]

    return response


def get_reply_thread(message_id: int):
    with engine.begin() as c:
        target_db = c.execute(
            select(web_messages_list.c.id, web_messages_list.c.content, web_authors_list.c.author_name,
                   web_authors_list.c.author_pfp, web_authors_list.c.author_username, web_messages_list.c.created_at,
                   web_messages_list.c.channel_id, web_messages_list.c.reply_msg)
            .join(web_authors_list, web_authors_list.c.id == web_messages_list.c.author_id)
            .where(web_messages_list.c.id == message_id)
        ).fetchone()
        if target_db is None:
            print("Target not found")
            return []

        replies = c.execute(
            select(web_messages_list.c.id, web_messages_list.c.content, web_authors_list.c.author_name,
                   web_authors_list.c.author_pfp, web_authors_list.c.author_username, web_messages_list.c.created_at,
                   web_messages_list.c.channel_id, web_messages_list.c.reply_msg)
            .join(web_authors_list, web_authors_list.c.id == web_messages_list.c.author_id)
            .where(web_messages_list.c.reply_msg == target_db[0])
        ).fetchall()

        msgs_db = [
            target_db,
            *replies
        ]

        if target_db[7] is not None:
            last_message_above = target_db

            while True:
                last_message_above = c.execute(
                    select(web_messages_list.c.id, web_messages_list.c.content, web_authors_list.c.author_name,
                           web_authors_list.c.author_pfp, web_authors_list.c.author_username, web_messages_list.c.created_at,
                           web_messages_list.c.channel_id, web_messages_list.c.reply_msg)
                    .join(web_authors_list, web_authors_list.c.id == web_messages_list.c.author_id)
                    .where(web_messages_list.c.id == last_message_above[7])
                ).fetchone()

                if last_message_above is None:
                    break

                msgs_db = [
                    last_message_above,
                    *msgs_db
                ]

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
            select(web_channels_list.c.name, web_channels_list.c.type)
            .where(web_channels_list.c.id == id)
        ).fetchone()

    if channel is None:
        return None

    if channel[1] == "thread":
        return f"{prefix}Thread: {channel[0]}"
    else:
        return f"{prefix}Channel #{channel[0]}"

def process_preferences():
    if "more_msgs" in request.form and request.form["more_msgs"] == "on":
        session["more"] = "1"
    else:
        session["more"] = "0"


def search_messages(query: str):
    with engine.begin() as c:
        messages_db = c.execute(
            select(web_messages_list.c.id, web_messages_list.c.content, web_authors_list.c.author_name,
                   web_authors_list.c.author_pfp, web_authors_list.c.author_username, web_messages_list.c.created_at,
                   web_messages_list.c.channel_id, web_messages_list.c.reply_msg)
            .where(web_messages_list.c.content.icontains(query))
            .join(web_authors_list, web_authors_list.c.id == web_messages_list.c.author_id)
            .order_by(web_messages_list.c.id.desc())
            .limit(10)
        ).fetchall()

        messages = _process_messages(c, messages_db)

    return messages