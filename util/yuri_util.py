import random

from sqlalchemy import Connection, select, update
from sqlalchemy.sql.functions import max

from database import yaoi_db, yuri_db


def get_some_yuri(conn: Connection) -> tuple[str | None, str | None]:
    """Returns relative path to yuri and source link and ticks it"""

    top_priority = conn.execute(select(max(yuri_db.c.priority))).fetchone()
    if not top_priority:
        return None, None

    top_priority = top_priority[0]

    yuri = conn.execute(
        select(yuri_db.c.id, yuri_db.c.filename, yuri_db.c.source).where(
            yuri_db.c.priority == top_priority
        )
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

    top_priority = conn.execute(select(max(yaoi_db.c.priority))).fetchone()
    if not top_priority:
        return None, None

    top_priority = top_priority[0]

    yaoi = conn.execute(
        select(yaoi_db.c.id, yaoi_db.c.filename, yaoi_db.c.source).where(
            yaoi_db.c.priority == top_priority
        )
    ).fetchall()

    yaoi = random.choice(yaoi)

    conn.execute(
        update(yaoi_db)
        .where(yaoi_db.c.id == yaoi[0])
        .values(priority=yaoi_db.c.priority - 1)
    )

    return yaoi[1], yaoi[2]
