import json
import os

from sqlalchemy import (
    BOOLEAN,
    VARCHAR,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    StaticPool,
    Table,
    create_engine,
)

if not os.path.exists("data"):
    os.mkdir("data")

engine = create_engine(
    os.getenv("DB_URL", "sqlite:///data/ai.db"),
    connect_args=json.loads(os.getenv("DB_ARGS") or "{}"),
    poolclass=StaticPool,
)

md_obj = MetaData()

cache_channel = Table(
    "cache_channel",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("cid", VARCHAR, unique=True),
    Column("name", VARCHAR, nullable=False),
    Column("topic", VARCHAR),
    Column("announcement", BOOLEAN, nullable=False, default=False),
    Column("nsfw", BOOLEAN, nullable=False, default=False),
)

cache_user = Table(
    "cache_user",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("uid", VARCHAR, unique=True),
    Column("username", VARCHAR, nullable=False),
    Column("displayname", VARCHAR, nullable=False),
    Column("avatar", VARCHAR),
    Column("bot", BOOLEAN, nullable=False, default=False),
)

cache_message = Table(
    "cache_message",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("mid", VARCHAR, unique=True),
    Column("cid", Integer, ForeignKey(cache_channel.c.id)),
    Column("uid", Integer, ForeignKey(cache_user.c.id)),
    Column("content", VARCHAR, nullable=False),
    Column("sentat", DateTime, nullable=False),
)

cache_embed = Table(
    "cache_embed",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("mid", Integer, ForeignKey(cache_message.c.id)),
    Column("title", VARCHAR),
    Column("description", VARCHAR),
    Column("authorname", VARCHAR),
    Column("authoravatar", VARCHAR),
    Column("footertext", VARCHAR),
)

cache_embed_field = Table(
    "cache_embed_field",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("eid", Integer, ForeignKey(cache_embed.c.id)),
    Column("name", VARCHAR, nullable=False),
    Column("value", VARCHAR, nullable=False),
)

fedi_notifications_ids = Table(
    "fedi_notifications",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("aid", VARCHAR, nullable=False, unique=True),
)

yt_notifications_ids = Table(
    "yt_notifications",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("ytid", VARCHAR, nullable=False, unique=True),
)

reports = Table(
    "reports",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("cid", VARCHAR, comment="Channel ID"),
    Column("mid", VARCHAR, comment="Message ID"),
    Column("aid", VARCHAR, comment="Message Author ID"),
    Column("rid", VARCHAR, comment="Reporter ID"),
    Column("lid", VARCHAR, comment="Log message ID"),
    Column("reason", VARCHAR),
)
