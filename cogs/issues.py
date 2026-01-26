import random

import aiohttp
from aiohttp import ClientResponseError
from discord import Cog, Bot, Interaction, InteractionType, InputTextStyle
from discord.ui import Modal, InputText

from constants import FORGEJO_INSTANCE, FORGEJO_TOKEN
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


def setup(bot: Bot):
    bot.add_cog(Issues(bot))
