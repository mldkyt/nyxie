import random

from sqlalchemy import Connection, select, update
from sqlalchemy.sql.functions import max

from database import yuri_db


def get_some_yuri(conn: Connection) -> tuple[str, str]:
    """Returns relative path to yuri and source link and ticks it"""

    top_priority = conn.execute(select(max(yuri_db.c.priority))).fetchone()
    if not top_priority:
        raise Exception("No yuri (no max priority detected)")

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
