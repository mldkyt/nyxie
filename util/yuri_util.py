import os
import random

from discord import ButtonStyle, Button, Interaction
from discord.ui import View, button
from sqlalchemy import Connection, select, update, delete
from sqlalchemy.sql.functions import max

from database import yaoi_db, yuri_db, engine


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

        await ctx.respond("Approved content", ephemeral=True)

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

        await ctx.respond("Rejected content", ephemeral=True)



def get_some_yuri(conn: Connection) -> tuple[str | None, str | None]:
    """Returns relative path to yuri and source link and ticks it"""

    top_priority = conn.execute(select(max(yuri_db.c.priority)).where(yuri_db.c.approved == 1)).fetchone()
    if not top_priority:
        return None, None

    top_priority = top_priority[0]

    yuri = conn.execute(
        select(yuri_db.c.id, yuri_db.c.filename, yuri_db.c.source).where(
            yuri_db.c.priority == top_priority
        ).where(yuri_db.c.approved == True)
    ).fetchall()

    yuri = random.choice(yuri)

    conn.execute(
        update(yuri_db)
        .where(yuri_db.c.id == yuri[0])
        .values(priority=yuri_db.c.priority - 1)
    )

    return yuri[1], yuri[2]


def get_some_yaoi(conn: Connection) -> tuple[str | None, str | None]:
    """Returns relative path to yaoi and source link and ticks it"""

    top_priority = conn.execute(select(max(yaoi_db.c.priority)).where(yaoi_db.c.approved == 1)).fetchone()
    if not top_priority:
        return None, None

    top_priority = top_priority[0]

    yaoi = conn.execute(
        select(yaoi_db.c.id, yaoi_db.c.filename, yaoi_db.c.source).where(
            yaoi_db.c.priority == top_priority
        ).where(yaoi_db.c.approved == True)
    ).fetchall()

    yaoi = random.choice(yaoi)

    conn.execute(
        update(yaoi_db)
        .where(yaoi_db.c.id == yaoi[0])
        .values(priority=yaoi_db.c.priority - 1)
    )

    return yaoi[1], yaoi[2]
