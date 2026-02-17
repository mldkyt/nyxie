import datetime
import os.path
import random

import aiohttp
from aiohttp import ClientResponseError
from discord import (
    Bot,
    ButtonStyle,
    Cog,
    InputTextStyle,
    Interaction,
    InteractionType,
    Message,
)
from discord.ext.tasks import loop
from discord.ui import (
    ActionRow,
    Button,
    Container,
    DesignerView,
    InputText,
    Modal,
    Separator,
    TextDisplay,
)
from sqlalchemy import delete, insert, select

from constants import (
    CHANNEL_MODERATION,
    CHANNEL_SUGGESTIONS,
    DEV_MODE,
    FORGEJO_INSTANCE,
    FORGEJO_TOKEN,
    GUILD,
)
from database import engine, suggestion_messages, suggestion_messages_comments
from logger import obsidian_logger


class ForgejoCreateIssueModal(Modal):
    def __init__(self, user: str, repo: str):
        super().__init__(title=f"create issue on {user}/{repo}")

        self.user = user
        self.repo = repo

        self.field_title = InputText(
            label="title",
            placeholder=random.choice(["fix this bug", "optimize this", "add shenanigans", "[feat] meowing"])
        )
        self.add_item(self.field_title)

        self.field_body = InputText(
            label="body",
            placeholder=random.choice(["i like meowing", "this is a detailed description...", "lain iwakura is an...",
                                       "add this new fancy feature that will revolutionize the world..."]),
            style=InputTextStyle.paragraph,
        )
        self.add_item(self.field_body)

    async def callback(self, interaction: Interaction):
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.post(f"https://{FORGEJO_INSTANCE}/api/v1/repos/{self.user}/{self.repo}/issues",
                                     headers={
                                         "Authorization": f"Bearer {FORGEJO_TOKEN}"
                                     }, json={
                            "title": self.field_title.value,
                            "body": f"User {interaction.user.display_name} ({interaction.user.name}, {interaction.user.id}) submitted the following:\n\n{self.field_body.value}",
                        }) as res:
                    res.raise_for_status()
                    res_b = await res.json()

                    await interaction.respond(
                        "issue created\nif the repository is public, see your issue here: "
                        f"https://{FORGEJO_INSTANCE}/{self.user}/{self.repo}/issues/{res_b['number']}",
                        ephemeral=True,
                    )
        except Exception as e:
            obsidian_logger.exception("An error occurred:")
            await interaction.respond("an error occurred, please try again later and probably tell Lunya",
                                      ephemeral=True)


class Issues(Cog):
    def __init__(self, bot: Bot):
        super().__init__()

        self.bot = bot

    suggestion_queue = []
    labels = []

    @Cog.listener()
    async def on_ready(self):
        async with aiohttp.ClientSession() as sess:
            async with sess.get(
                    f"https://{FORGEJO_INSTANCE}/api/v1/repos/lunya/DiscordServer/labels"
                    if DEV_MODE == "0" else
                    f"https://{FORGEJO_INSTANCE}/api/v1/repos/lunya/test/labels",
                    headers={
                        "Authorization": f"Bearer {FORGEJO_TOKEN}"
                    }) as res:
                res.raise_for_status()
                labels = await res.json()

                for i in labels:
                    self.labels.append((i['id'], i['name']))

        self.queue_suggestions.start()
        self.update_thread_titles.start()

    def get_labels(self, *labels: str) -> list[int]:
        a = []
        for i in self.labels:
            if i[1] in labels:
                a.append(i[0])

        return a

    @Cog.listener()
    async def on_interaction(self, interaction: Interaction):
        try:
            if interaction.type != InteractionType.component:
                return

            if not interaction.custom_id.startswith("br"):  # |B|ug |R|eporting
                return

            split = interaction.custom_id.split(":")
            if len(split) != 2:
                return

            project_params = split[1].split("/")
            if len(project_params) != 2:
                return

            owner = project_params[0]
            repo = project_params[1]

            # Verify repo
            async with aiohttp.ClientSession() as sess:
                async with sess.get(f"https://{FORGEJO_INSTANCE}/api/v1/repos/{owner}/{repo}", headers={
                    'Authorization': f'Bearer {FORGEJO_TOKEN}'
                }) as req:
                    req.raise_for_status()

            modal = ForgejoCreateIssueModal(owner, repo)
            await interaction.response.send_modal(modal)
        except ClientResponseError as e:
            await interaction.respond(f"An error occured while contacting the server, {e.status} {e.message}",
                                      ephemeral=True)
            obsidian_logger.warning(f"Repo doesn't exist: %s %s", e.status, e.message)
        except Exception:
            obsidian_logger.exception("Error handling on_interaction inside Bug Reporting")

    @Cog.listener()
    async def on_message(self, message: Message):
        if message.author.bot:
            return

        if message.channel.id == int(CHANNEL_SUGGESTIONS):
            self.suggestion_queue.append(
                (message.id, message.content, message.author, datetime.datetime.now())
            )

        await self.add_comment(message)

    async def add_comment(self, message: Message):
        with engine.begin() as c:
            a = c.execute(
                select(
                    suggestion_messages.c.id,
                    suggestion_messages.c.tracker_id
                )
                .where(suggestion_messages.c.thread_id == str(message.channel.id))
            ).fetchone()

        if a is not None:
            # Add comment
            async with aiohttp.ClientSession() as sess:
                async with sess.post(
                        f"https://{FORGEJO_INSTANCE}/api/v1/repos/lunya/DiscordServer/issues/{a[1]}/comments"
                        if DEV_MODE == "0" else
                        f"https://{FORGEJO_INSTANCE}/api/v1/repos/lunya/test/issues/{a[1]}/comments",
                        headers={
                            "Authorization": f"Bearer {FORGEJO_TOKEN}"
                        }, json={
                            "body": f"{message.author.display_name} ({message.author.name}; {message.author.id}) said:\n\n{message.content}"
                        }) as res:
                    res.raise_for_status()

                    out = await res.json()

                    with engine.begin() as c:
                        c.execute(
                            insert(suggestion_messages_comments)
                            .values(suggestion_id=a[0], comment_id=out["id"], message_id=str(message.id))
                        )

            # Attachments
            if not os.path.exists("tmp"):
                os.mkdir("tmp")

            # Download
            for attachment in message.attachments:
                async with aiohttp.ClientSession() as sess:
                    async with sess.get(attachment.url) as req:
                        if not req.ok:
                            obsidian_logger.warning("Failed to download %s", attachment.filename)
                            continue

                        data = await req.read()

                        with open(f"tmp/{attachment.filename}", "wb") as f:
                            f.write(data)

            # Upload
            for attachment in message.attachments:
                if not os.path.exists(f'tmp/{attachment.filename}'):
                    obsidian_logger.warning("Tried to upload non-existent file %s", attachment.filename)
                    continue

                async with aiohttp.ClientSession() as sess:
                    async with sess.post(
                            f"https://{FORGEJO_INSTANCE}/api/v1/repos/lunya/DiscordServer/issues/comments/{out['id']}/assets"
                            if DEV_MODE == "0" else
                            f"https://{FORGEJO_INSTANCE}/api/v1/repos/lunya/test/issues/comments/{out['id']}/assets",
                            headers={
                                "Authorization": f"Bearer {FORGEJO_TOKEN}"
                            },
                            data={
                                "attachment": open(f"tmp/{attachment.filename}", "rb")
                            }) as res:
                        if not res.ok:
                            text = await res.text()
                            obsidian_logger.warning("File failed to upload: %s: %s %s", attachment.filename,
                                                    str(res.status), text)

            # Delete locally
            for attachment in message.attachments:
                if os.path.exists(f"tmp/{attachment.filename}"):
                    os.remove(f"tmp/{attachment.filename}")


    @Cog.listener()
    async def on_message_delete(self, message: Message):
        if message.author.bot:
            return

        await self.on_delete_close_issue(message)
        await self.on_delete_comment(message)

    async def on_delete_comment(self, message: Message):
        with engine.begin() as c:
            a = c.execute(
                select(
                    suggestion_messages_comments.c.id,
                    suggestion_messages_comments.c.comment_id
                )
                .where(suggestion_messages_comments.c.message_id == str(message.id))
            ).fetchone()

        if a is not None:
            # Delete comment
            async with aiohttp.ClientSession() as sess:
                async with sess.delete(
                        f"https://{FORGEJO_INSTANCE}/api/v1/repos/lunya/DiscordServer/issues/comments/{a[1]}"
                        if DEV_MODE == "0" else
                        f"https://{FORGEJO_INSTANCE}/api/v1/repos/lunya/test/issues/comments/{a[1]}",
                        headers={
                            "Authorization": f"Bearer {FORGEJO_TOKEN}"
                        }) as res:
                    res.raise_for_status()

                    with engine.begin() as c:
                        c.execute(
                            delete(suggestion_messages_comments)
                            .where(suggestion_messages_comments.c.id == a[0])
                        )

    async def on_delete_close_issue(self, message: Message):
        if message.channel.id == int(CHANNEL_SUGGESTIONS):
            self.suggestion_queue = [i for i in self.suggestion_queue
                                     if i[0] != message.id]

            a = None
            with engine.begin() as c:
                a = c.execute(
                    select(suggestion_messages)
                    .where(suggestion_messages.c.message_id == str(message.id))
                ).fetchone()

            if a is not None:
                await self.close_issue(a)

    # assume tuple[ID, message ID, tracker ID]
    async def close_issue(self, a: tuple[int, str, int, str, str]):
        async with aiohttp.ClientSession() as sess:
            async with sess.patch(
                    f"https://{FORGEJO_INSTANCE}/api/v1/repos/lunya/DiscordServer/issues/{a[2]}"
                    if DEV_MODE == "0" else
                    f"https://{FORGEJO_INSTANCE}/api/v1/repos/lunya/test/issues/{a[2]}",
                    headers={
                        "Authorization": f"Bearer {FORGEJO_TOKEN}"
                    }, json={
                        "state": "closed"
                    }) as res:
                res.raise_for_status()

        reply_msg = await self.bot.get_guild(int(GUILD)).get_channel(int(CHANNEL_SUGGESTIONS)).get_thread(int(a[4])).fetch_message(int(a[3]))
        await reply_msg.delete()
        thread = self.bot.get_guild(int(GUILD)).get_channel(int(CHANNEL_SUGGESTIONS)).get_thread(int(a[4]))
        await thread.archive()

        component = Container(
            TextDisplay("# Issue Closed"),
            Separator(),
            ActionRow(
                Button(label="Forgejo", style=ButtonStyle.url, url=f"https://{FORGEJO_INSTANCE}/lunya/DiscordServer/issues/{a[2]}"),
                Button(label="Thread", style=ButtonStyle.url, url=thread.jump_url)
            )
        )

        logs_channel = self.bot.get_guild(int(GUILD)).get_channel(int(CHANNEL_MODERATION))
        await logs_channel.send(view=DesignerView(component))

    @loop(seconds=1)
    async def queue_suggestions(self):
        try:
            if len(self.suggestion_queue) == 0:
                return

            a = self.suggestion_queue.pop()
            if (datetime.datetime.now() - a[3]).total_seconds() < 10:
                self.suggestion_queue.append(a)
                return

            obsidian_logger.info("Suggestions queue: 1 active, %d queued", len(self.suggestion_queue))

            async with aiohttp.ClientSession() as sess:
                async with sess.post(
                        f"https://{FORGEJO_INSTANCE}/api/v1/repos/lunya/DiscordServer/issues"
                        if DEV_MODE == "0" else
                        f"https://{FORGEJO_INSTANCE}/api/v1/repos/lunya/test/issues",
                        headers={
                            "Authorization": f"Bearer {FORGEJO_TOKEN}"
                        }, json={
                            "title": f"[Suggestion] {a[1][:30]}...",
                            "body": f"User {a[2].display_name} ({a[2].name}, {a[2].id}) suggested the following in the Discord server suggestions channel:\n\n{a[1]}",
                            "labels": self.get_labels("Status/Update Title")
                        }) as res:
                    res.raise_for_status()
                    res_b = await res.json()

            guild = self.bot.get_guild(int(GUILD))
            channel = guild.get_channel(int(CHANNEL_SUGGESTIONS))
            message = await channel.fetch_message(a[0])

            # Attachments
            if not os.path.exists("tmp"):
                os.mkdir("tmp")

            # Download
            for attachment in message.attachments:
                async with aiohttp.ClientSession() as sess:
                    async with sess.get(attachment.url) as req:
                        if not req.ok:
                            obsidian_logger.warning("Failed to download %s", attachment.filename)
                            continue

                        data = await req.read()

                        with open(f"tmp/{attachment.filename}", "wb") as f:
                            f.write(data)

            # Upload
            for attachment in message.attachments:
                if not os.path.exists(f'tmp/{attachment.filename}'):
                    obsidian_logger.warning("Tried to upload non-existent file %s", attachment.filename)
                    continue

                async with aiohttp.ClientSession() as sess:
                    async with sess.post(
                            f"https://{FORGEJO_INSTANCE}/api/v1/repos/lunya/DiscordServer/issues/{res_b['number']}/assets"
                            if DEV_MODE == "0" else
                            f"https://{FORGEJO_INSTANCE}/api/v1/repos/lunya/test/issues/{res_b['number']}/assets",
                            headers={
                                "Authorization": f"Bearer {FORGEJO_TOKEN}"
                            },
                            data={
                                "attachment": open(f"tmp/{attachment.filename}", "rb")
                            }) as res:
                        if not res.ok:
                            text = await res.text()
                            obsidian_logger.warning("File failed to upload: %s: %s %s", attachment.filename,
                                                    str(res.status), text)

            # Delete locally
            for attachment in message.attachments:
                if os.path.exists(f"tmp/{attachment.filename}"):
                    os.remove(f"tmp/{attachment.filename}")

            thread = await message.create_thread(name=f"[Suggestion] {a[1][:30]}...")
            reply = await thread.send(
                f"{message.author.mention}\n"
                f"[You can track your suggestion here](https://{FORGEJO_INSTANCE}/lunya/DiscordServer/issues/{res_b['number']}). "
                f"You can close the issue by deleting the suggestion, and you'll be able to see posted comments here. ")

            with engine.begin() as c:
                c.execute(
                    insert(suggestion_messages)
                    .values(message_id=str(a[0]), tracker_id=res_b['number'], reply_id=str(reply.id), thread_id=str(thread.id))
                )

            component = Container(
                TextDisplay("# Issue Created"),
                Separator(),
                ActionRow(
                    Button(label="Forgejo", style=ButtonStyle.link, url=f"https://{FORGEJO_INSTANCE}/lunya/DiscordServer/issues/{res_b['number']}"),
                    Button(label="Message", style=ButtonStyle.link, url=message.jump_url),
                    Button(label="Thread", style=ButtonStyle.link, url=thread.jump_url)
                )
            )

            logs_channel = guild.get_channel(int(CHANNEL_MODERATION))
            await logs_channel.send(view=DesignerView(component))
        except Exception:
            obsidian_logger.exception("An error occured during suggestion queue execution:")

    @loop(minutes=5)
    async def update_thread_titles(self):
        async with aiohttp.ClientSession() as sess:
            async with sess.get(
                    f"https://{FORGEJO_INSTANCE}/api/v1/repos/lunya/DiscordServer/issues"
                    if DEV_MODE == "0" else
                    f"https://{FORGEJO_INSTANCE}/api/v1/repos/lunya/test/issues",
                    headers={
                        "Authorization": f"Bearer {FORGEJO_TOKEN}"
                    }, params={
                        "type": "issues",
                        "state": "open"
                    }) as res:
                res.raise_for_status()
                issues_json = await res.json()

        # {issue_id, json_of_issue}
        issues_numbers = {}

        with engine.begin() as c:
            for i in issues_json:
                thread_id = c.execute(
                    select(suggestion_messages.c.thread_id)
                    .where(suggestion_messages.c.tracker_id == i["number"])
                ).fetchone()

                if thread_id is None:
                    continue

                issues_numbers[thread_id[0]] = i

        for issue_thread_id, issue in issues_numbers.items():
            thread = self.bot.get_guild(int(GUILD)).get_channel(int(CHANNEL_SUGGESTIONS)).get_thread(
                int(issue_thread_id))
            if thread is None:
                continue
            if thread.archived:
                continue

            if thread.name.strip() != issue["title"].strip():
                await thread.edit(name=issue["title"].strip())
                obsidian_logger.info("Updated thread name for issue %d to %s on Discord", issue["number"],
                                     issue["title"])


def setup(bot: Bot):
    bot.add_cog(Issues(bot))
