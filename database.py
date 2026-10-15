import json
import os

from sqlalchemy import (
    BOOLEAN,
    VARCHAR,
    BigInteger,
    Column,
    DateTime,
    ForeignKeyConstraint,
    Integer,
    MetaData,
    StaticPool,
    Table,
    create_engine,
)

if not os.path.exists("data"):
    os.mkdir("data")

engine = create_engine(
    os.getenv("DB_URL", "sqlite:///data/nyxie.db"),
    connect_args=json.loads(os.getenv("DB_ARGS") or "{}"),
    poolclass=StaticPool,
)

md_obj = MetaData()

dm_channels = Table(
    "dm_channel",
    md_obj,
    Column("user_id", VARCHAR, primary_key=True),
    Column("channel_id", VARCHAR, primary_key=True),
)

web_authors_list = Table(
    "authors",
    md_obj,
    Column("id", BigInteger, primary_key=True),
    Column("author_name", VARCHAR, nullable=False),
    Column("author_pfp", VARCHAR, nullable=False),
    Column("author_username", VARCHAR),  # the same way usernames on Discord are unique
    Column("consent", Integer, server_default="0"),
)

web_channels_list = Table(
    "channels",
    md_obj,
    Column("id", BigInteger, primary_key=True),
    Column("type", VARCHAR, server_default="channel"),
    Column("name", VARCHAR, nullable=False),
    Column("category", VARCHAR),
    Column("position", Integer),
)

web_messages_list = Table(
    "messages",
    md_obj,
    Column("id", BigInteger, primary_key=True),
    Column("content", VARCHAR, nullable=False),
    Column("author_id", BigInteger, nullable=False),
    Column("channel_id", BigInteger, nullable=False),
    Column("reply_msg", BigInteger),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default="now()"
    ),
    Column("pinned", Integer, server_default="0", nullable=False),
    # this will get updated by the _update_message method
    ForeignKeyConstraint(
        ["author_id"], ["authors.id"], onupdate="CASCADE", ondelete="CASCADE"
    ),
    ForeignKeyConstraint(
        ["reply_msg"], ["messages.id"], onupdate="CASCADE", ondelete="SET NULL"
    ),
    ForeignKeyConstraint(
        ["channel_id"], ["channels.id"], onupdate="CASCADE", ondelete="CASCADE"
    ),
)

web_messages_attachments_list = Table(
    "message_attachments",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("message_id", BigInteger, nullable=False),
    Column("attachment_name", VARCHAR, nullable=False),
    Column("attachment_url", VARCHAR, nullable=False),
    ForeignKeyConstraint(
        ["message_id"], ["messages.id"], onupdate="CASCADE", ondelete="CASCADE"
    ),
)

# priority gets decreased by one every single time the image is fetched, so that yuri is "infinite
yuri_db = Table(
    "yuri",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("priority", Integer, default=10000, nullable=False),
    Column("filename", VARCHAR, nullable=False),
    Column("source", VARCHAR, nullable=False),
    Column("approved", BOOLEAN, nullable=False, server_default="0"),
    Column("cw", VARCHAR, nullable=False, server_default=""),
    Column("alt", VARCHAR, nullable=False, server_default=""),
)

# priority gets decreased by one every single time the image is fetched, so that yaoi is "infinite
yaoi_db = Table(
    "yaoi",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("priority", Integer, default=10000, nullable=False),
    Column("filename", VARCHAR, nullable=False),
    Column("source", VARCHAR, nullable=False),
    Column("approved", BOOLEAN, nullable=False, server_default="0"),
    Column("cw", VARCHAR, nullable=False, server_default=""),
    Column("alt", VARCHAR, nullable=False, server_default=""),
)

alt_text_suggestions = Table(
    "alt_text_suggestions",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("fid", Integer, nullable=False),
    Column("type", VARCHAR, nullable=False),
    Column("alt", VARCHAR, nullable=False),
)

cw_suggestions = Table(
    "cw_suggestions",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("fid", Integer, nullable=False),
    Column("type", VARCHAR, nullable=False),
    Column("cw", VARCHAR, nullable=False),
)

acknowledged_notifications = Table(
    "acknowledged_notifications", md_obj, Column("id", VARCHAR, primary_key=True)
)

verifications = Table(
    "verifications",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("moderator_message_id", VARCHAR, nullable=False),
    Column("member_id", VARCHAR, nullable=False),
)

kv = Table(
    "kv",
    md_obj,
    Column("uid", VARCHAR, primary_key=True),
    Column("name", VARCHAR, primary_key=True),
    Column("value", VARCHAR),
)