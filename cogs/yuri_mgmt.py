from discord import Cog, SlashCommandGroup, ApplicationContext, Bot, User
from sqlalchemy import update, insert, select, delete

from constants import OWNER, GUILD
from database import engine, yuri_db, yaoi_db, yuri_authorized_users


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

    @yuri_management.command(name="authorize")
    async def authorize(self, ctx: ApplicationContext,
                        user: User):
        """Authorize user to yuri/yaoi commands"""

        if ctx.user.id != int(OWNER):
            await ctx.respond("This is limited to owner of bot only", ephemeral=True)
            return

        with engine.begin() as c:
            if c.execute(
                    select(yuri_authorized_users.c.id)
                            .where(yuri_authorized_users.c.uid == str(user.id))
            ).fetchone() is not None:
                await ctx.respond("This user is already authorized", ephemeral=True)
                return

            c.execute(
                insert(yuri_authorized_users)
                .values(uid=str(user.id))
            )

        await ctx.respond("User was authorized", ephemeral=True)

    @yuri_management.command(name="deauthorize")
    async def deauthorize(self, ctx: ApplicationContext,
                          user: User):
        """Deauthorize user to yuri/yaoi commands"""

        if ctx.user.id != int(OWNER):
            await ctx.respond("This is limited to owner of bot only", ephemeral=True)
            return

        with engine.begin() as c:
            if c.execute(
                    select(yuri_authorized_users.c.id)
                            .where(yuri_authorized_users.c.uid == str(user.id))
            ).fetchone() is None:
                await ctx.respond("This user is not authorized", ephemeral=True)
                return

            c.execute(
                delete(yuri_authorized_users)
                .where(yuri_authorized_users.c.uid == str(user.id))
            )

        await ctx.respond("User was deauthorized", ephemeral=True)


def setup(bot: Bot):
    bot.add_cog(YuriMgmt(bot))
