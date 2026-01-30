import datetime
import random

import aiohttp
from aiohttp import ClientResponseError
from discord import Cog, Bot, Interaction, InteractionType, InputTextStyle, Message
from discord.ext.tasks import loop
from discord.ui import Modal, InputText
from sqlalchemy import insert, select

from constants import FORGEJO_INSTANCE, FORGEJO_TOKEN, GUILD, DEV_MODE, CHANNEL_SUGGESTIONS
from database import engine, suggestion_messages
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
        if message.channel.id != int(CHANNEL_SUGGESTIONS):
            return
        if message.author.bot:
            return

        self.suggestion_queue.append(
            (message.id, message.content, message.author, datetime.datetime.now())
        )

    @Cog.listener()
    async def on_message_delete(self, message: Message):
        if message.channel.id != int(CHANNEL_SUGGESTIONS):
            return
        if message.author.bot:
            return

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
    async def close_issue(self, a: tuple[int, str, int, str]):
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

        reply_msg = await self.bot.get_guild(int(GUILD)).get_channel(int(CHANNEL_SUGGESTIONS)).fetch_message(int(a[3]))
        await reply_msg.delete()

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

            reply = await message.reply(
                f"[You can track your suggestion here](https://{FORGEJO_INSTANCE}/lunya/DiscordServer/issues/{res_b['number']}). "
                f"You can close the issue by deleting the suggestion, and you'll be able to see posted comments here. ")

            with engine.begin() as c:
                c.execute(
                    insert(suggestion_messages)
                    .values(message_id=str(a[0]), tracker_id=res_b['number'], reply_id=str(reply.id))
                )
        except Exception:
            obsidian_logger.exception("An error occured during suggestion queue execution:")


def setup(bot: Bot):
    bot.add_cog(Issues(bot))
