import discord
from discord import ApplicationContext, Bot, Member
from sentry_sdk import capture_exception

from constants import GUILD, OWNER
from util.dm import dm_cache


class DevCommands(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    dev_group = discord.SlashCommandGroup(
        name="dev",
        description="Developer commands",
        guild_ids=[int(GUILD)],
        default_member_permissions=discord.Permissions(administrator=True),
    )

    @dev_group.command(name="debug")
    async def debug_cmd(self, ctx: discord.ApplicationContext):
        await ctx.respond("Debug command", ephemeral=True)

    @dev_group.command(name="send_test_dm")
    async def send_test_dm(self, ctx: ApplicationContext, user: Member, message: str):
        try:
            if ctx.user.id != int(OWNER):
                await ctx.respond(
                    "You are not authorized to use this command!", ephemeral=True
                )
                return

            dm_cache.add_dm_to_send(user.id, message)
            await ctx.respond("Dm will be sent", ephemeral=True)
        except Exception as e:
            capture_exception(e)
            await ctx.respond("an error occured", ephemeral=True)


def setup(bot: Bot):
    bot.add_cog(DevCommands(bot))
