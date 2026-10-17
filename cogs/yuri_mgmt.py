from discord import Cog, SlashCommandGroup, ApplicationContext, Bot
from sqlalchemy import update

from constants import OWNER, GUILD
from database import engine, yuri_db, yaoi_db


class YuriMgmt(Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot

    yuri_management = SlashCommandGroup("yuri_mgmt", guild_ids=[int(GUILD)])

    @yuri_management.command(name="yuri")
    async def update_yuri(self, ctx: ApplicationContext,
                          id: int,
                          cw: str | None = None,
                          remove_cw: bool = False,
                          alt: str | None = None,
                          remove_alt: bool = False):
        """Edit yuri entry"""
        if ctx.user.id != int(OWNER):
            await ctx.respond("This is limited to owner of bot only", ephemeral=True)
            return

        with engine.begin() as c:
            if cw is not None or remove_cw:
                c.execute(
                    update(yuri_db)
                    .values(cw="" if remove_cw else cw)
                    .where(yuri_db.c.id == id)
                )
            if alt is not None or remove_alt:
                c.execute(
                    update(yuri_db)
                    .values(alt="" if remove_alt else alt)
                    .where(yuri_db.c.id == id)
                )

        await ctx.respond("Updated yuri entry", ephemeral=True)

    @yuri_management.command(name="yaoi")
    async def update_yaoi(self, ctx: ApplicationContext,
                          id: int,
                          cw: str | None = None,
                          remove_cw: bool = False,
                          alt: str | None = None,
                          remove_alt: bool = False):
        """Edit yaoi entry"""
        if ctx.user.id != int(OWNER):
            await ctx.respond("This is limited to owner of bot only", ephemeral=True)
            return

        with engine.begin() as c:
            if cw is not None or remove_cw:
                c.execute(
                    update(yaoi_db)
                    .values(cw="" if remove_cw else cw)
                    .where(yaoi_db.c.id == id)
                )
            if alt is not None:
                c.execute(
                    update(yaoi_db)
                    .values(alt="" if remove_alt else alt)
                    .where(yaoi_db.c.id == id)
                )

        await ctx.respond("Updated yaoi entry", ephemeral=True)


def setup(bot: Bot):
    bot.add_cog(YuriMgmt(bot))
