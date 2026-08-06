import os
import random

from discord import ButtonStyle, Button, Interaction, Embed, File
from discord.ui import View, button, Modal, InputText
from sqlalchemy import Connection, select, update, delete
from sqlalchemy.sql.functions import max

from database import yaoi_db, yuri_db, engine


async def respond_with_next_yuri(ctx: Interaction, reapprove: bool = False) -> bool:
    with engine.begin() as c:
        if reapprove:
            c.execute(
                update(yuri_db)
                .values(approved=False)
            )
            c.execute(
                update(yaoi_db)
                .values(approved=False)
            )

        yuri = c.execute(
            select(yuri_db.c.id, yuri_db.c.filename)
            .where(yuri_db.c.approved == False)
        ).fetchone()

        if yuri is not None:
            await ctx.respond(view=YuriApproval("yuri", yuri[0]),
                              embed=Embed(
                                  title="Approve this yuri",
                                  image=f"attachment://{yuri[1].split('/')[-1]}",
                              ),
                              file=File(yuri[1]),
                              ephemeral=True)
            return True

        yaoi = c.execute(
            select(yaoi_db.c.id, yaoi_db.c.filename)
            .where(yaoi_db.c.approved == False)
        ).fetchone()

        if yaoi is not None:
            await ctx.respond(view=YuriApproval("yaoi", yaoi[0]),
                              embed=Embed(
                                  title="Approve this yaoi",
                                  image=f"attachment://{yaoi[1].split('/')[-1]}",
                              ),
                              file=File(yaoi[1]),
                              ephemeral=True)
            return True

    return False


class YuriCWModal(Modal):
    def __init__(self, type: str, id: int):
        super().__init__(title=f"CW this {type}")
        self.type = type
        self.content_id = id
        self.cw = InputText(label="CW", placeholder="suggestive")
        self.add_item(self.cw)

    async def callback(self, interaction: Interaction):
        new_cw = self.cw.value or ""

        with engine.begin() as c:
            if self.type == "yuri":
                c.execute(
                    update(yuri_db)
                    .where(yuri_db.c.id == self.content_id)
                    .values(cw=new_cw)
                )
            elif self.type == "yaoi":
                c.execute(
                    update(yaoi_db)
                    .where(yaoi_db.c.id == self.content_id)
                    .values(cw=new_cw)
                )

        await interaction.respond("CW" + ("updated" if len(new_cw) > 0 else "removed"), ephemeral=True)


class YuriApproval(View):
    def __init__(self, type: str, content_id: int):
        super().__init__()

        self.type = type
        self.content_id = content_id

    @button(label="Approve", style=ButtonStyle.green)
    async def approve_yuri(self, button: Button, ctx: Interaction):
        with engine.begin() as c:
            if self.type == "yuri":
                c.execute(
                    update(yuri_db)
                    .where(yuri_db.c.id == self.content_id)
                    .values(approved=True)
                )
            elif self.type == "yaoi":
                c.execute(
                    update(yaoi_db)
                    .where(yaoi_db.c.id == self.content_id)
                    .values(approved=True)
                )

        if not await respond_with_next_yuri(ctx):
            await ctx.respond("All done!", ephemeral=True)

    @button(label="Reject", style=ButtonStyle.red)
    async def reject_yuri(self, button: Button, ctx: Interaction):
        with engine.begin() as c:
            if self.type == "yuri":
                yuri = c.execute(
                    select(yuri_db.c.filename)
                    .where(yuri_db.c.id == self.content_id)
                ).fetchone()

                if yuri is None:
                    return

                os.remove(yuri[0])

                c.execute(
                    delete(yuri_db)
                    .where(yuri_db.c.id == self.content_id)
                )
            elif self.type == "yaoi":
                yaoi = c.execute(
                    select(yaoi_db.c.filename)
                    .where(yaoi_db.c.id == self.content_id)
                ).fetchone()

                if yaoi is None:
                    return

                os.remove(yaoi[0])

                c.execute(
                    delete(yaoi_db)
                    .where(yaoi_db.c.id == self.content_id)
                )

        if not await respond_with_next_yuri(ctx):
            await ctx.respond("All done!", ephemeral=True)
            
    @button(label="Set CW", style=ButtonStyle.secondary)
    async def set_cw(self, button: Button, interaction: Interaction):
        await interaction.response.send_modal(YuriCWModal(self.type, self.content_id))



def get_some_yuri(conn: Connection) -> tuple[str | None, str | None, str | None, str | None]:
    """Returns relative path to yuri and source link and ticks it"""

    top_priority = conn.execute(select(max(yuri_db.c.priority)).where(yuri_db.c.approved == True)).fetchone()
    if not top_priority:
        return None, None, None, None

    top_priority = top_priority[0]

    yuri = conn.execute(
        select(yuri_db.c.id, yuri_db.c.filename, yuri_db.c.source, yuri_db.c.cw, yuri_db.c.alt).where(
            yuri_db.c.priority == top_priority
        ).where(yuri_db.c.approved == True)
    ).fetchall()

    yuri = random.choice(yuri)

    conn.execute(
        update(yuri_db)
        .where(yuri_db.c.id == yuri[0])
        .values(priority=yuri_db.c.priority - 1)
    )

    return yuri[1], yuri[2], yuri[3], yuri[4]


def get_some_yaoi(conn: Connection) -> tuple[str | None, str | None, str | None, str | None]:
    """Returns relative path to yaoi and source link and ticks it"""

    top_priority = conn.execute(select(max(yaoi_db.c.priority)).where(yaoi_db.c.approved == True)).fetchone()
    if not top_priority:
        return None, None, None, None

    top_priority = top_priority[0]

    yaoi = conn.execute(
        select(yaoi_db.c.id, yaoi_db.c.filename, yaoi_db.c.source, yaoi_db.c.cw, yaoi_db.c.alt).where(
            yaoi_db.c.priority == top_priority
        ).where(yaoi_db.c.approved == True)
    ).fetchall()

    yaoi = random.choice(yaoi)

    conn.execute(
        update(yaoi_db)
        .where(yaoi_db.c.id == yaoi[0])
        .values(priority=yaoi_db.c.priority - 1)
    )

    return yaoi[1], yaoi[2], yaoi[3], yaoi[4]
