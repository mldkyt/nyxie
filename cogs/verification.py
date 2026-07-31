from discord import Cog, Bot, slash_command, ApplicationContext, default_permissions, Member, Embed, Color, \
    HTTPException, Forbidden
from discord.ext.pages import Paginator
from discord.ext.tasks import loop
from sentry_sdk import capture_exception

from util.verification import unverified_members, RejoinView


class Verification(Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot
        self.kick_members: list[Member] = []

    @Cog.listener()
    async def on_ready(self):
        self.kick_member.start()

    @slash_command()
    @default_permissions(administrator=True)
    async def list_unverified(self, ctx: ApplicationContext):
        """List unverified users"""
        await ctx.defer(ephemeral=True)

        members: list[Member] = []
        async for member in unverified_members(ctx.guild):
            members.append(member)

        pages = []
        current_page = "# Members that are about to be kicked: \n\n"
        for member in members:
            current_page += f"- {member.display_name} ({member.name}, {member.id})\n"

            if len(current_page) > 1000:
                pages.append(current_page)
                current_page = "\n"

        if len(current_page) > 0:
            pages.append(current_page)

        paginator = Paginator(pages)
        await paginator.respond(ctx.interaction, ephemeral=True)

    @slash_command()
    @default_permissions(administrator=True)
    async def kick_unverified(self, ctx: ApplicationContext, confirm: bool = False, i_really_want_to_kick_members: bool = False):
        """Kick unverified users"""
        if not confirm or not i_really_want_to_kick_members:
            await ctx.respond("The action was not confirmed", ephemeral=True)
            return

        members: list[Member] = []
        async for member in unverified_members(ctx.guild):
            members.append(member)

        self.kick_members.extend(members)
        await ctx.respond(f"Kicking {len(members)} members queued", ephemeral=True)

    @loop(seconds=5)
    async def kick_member(self):
        if len(self.kick_members) == 0:
            return

        try:
            kick_this_member = self.kick_members[0]
            try:
                await kick_this_member.send(embed=Embed(
                    title="Kicked",
                    description="You have been kicked from mldkyt's Discord server for not verifying in the specified time window.\n"
                                "\n"
                                "Don't worry! You can rejoin using the button below and verify again.",
                    color=Color.red(),
                ), view=RejoinView())
            except HTTPException | Forbidden:
                pass

            await kick_this_member.kick(reason="Not verified in time period")

            self.kick_members.remove(kick_this_member)
        except Exception as e:
            capture_exception(e)


def setup(bot: Bot):
    bot.add_cog(Verification(bot))
