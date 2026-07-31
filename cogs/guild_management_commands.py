import aiohttp
from aiohttp import ClientResponseError
from discord import Cog, Bot, SlashCommandGroup, Permissions, ApplicationContext
from discord.ui import View, Button
from sentry_sdk import capture_exception

from constants import GUILD, OWNER, FORGEJO_INSTANCE, FORGEJO_TOKEN


class GuildManagementCommands(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    guild_management_group = SlashCommandGroup(name="guild_management",
                                               default_member_permissions=Permissions(administrator=True),
                                               guild_ids=[int(GUILD)])

    @guild_management_group.command()
    async def send_project_button(self, ctx: ApplicationContext, message: str, button_label: str, owner: str,
                                  repo: str):
        try:
            if ctx.user.id != int(OWNER):
                await ctx.respond("you are not intended to run this", ephemeral=True)
                return

            # Verify repo
            async with aiohttp.ClientSession() as sess:
                async with sess.get(f"https://{FORGEJO_INSTANCE}/api/v1/repos/{owner}/{repo}", headers={
                    'Authorization': f'Bearer {FORGEJO_TOKEN}'
                }) as req:
                    req.raise_for_status()

            view = View()
            view.add_item(
                Button(label=button_label, custom_id=f"br:{owner}/{repo}")
            )
            await ctx.channel.send(message, view=view)
            await ctx.respond("Sent", ephemeral=True)
        except ClientResponseError as e:
            await ctx.respond(f"An error occured while contacting the server, {e.status} {e.message}", ephemeral=True)
        except Exception as e:
            capture_exception(e)
            await ctx.respond("An error occured, forgejo is down or repo doesn't exist", ephemeral=True)


def setup(bot: Bot):
    bot.add_cog(GuildManagementCommands(bot))
