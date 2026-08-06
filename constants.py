import os

from dotenv import load_dotenv

load_dotenv()

VERSION = "@VERSION@"

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

GUILD = os.getenv("GUILD")
OWNER = os.getenv("OWNER")

CHANNEL_MEMES = os.getenv("CHANNEL_MEMES")

CHANNEL_YURI = os.getenv("CHANNEL_YURI")
CHANNEL_YAOI = os.getenv("CHANNEL_YAOI")
CHANNEL_MEOW = os.getenv("CHANNEL_MEOW")

CHANNEL_MODERATION = os.getenv("CHANNEL_MODERATION")
CHANNEL_SUGGESTIONS = os.getenv("CHANNEL_SUGGESTIONS")

WEB_TOKEN = os.getenv("WEB_TOKEN")


MEMBER_ROLE = os.getenv("MEMBER_ROLE")

SENTRY_SDK = os.getenv("SENTRY_SDK")

def validate_values(l: dict[str, str | None]):
    for k, v in l.items():
        if v is None:
            print(f"CONSTANTS: The constant value for {k} is NOT set!")


validate_values(
    {
        "DISCORD_TOKEN": DISCORD_TOKEN,
        "GUILD": GUILD,
        "OWNER": OWNER,
        "CHANNEL_MEMES": CHANNEL_MEMES,
        "CHANNEL_YURI": CHANNEL_YURI,
        "CHANNEL_YAOI": CHANNEL_YAOI,
        "CHANNEL_MEOW": CHANNEL_MEOW,
        "CHANNEL_MODERATION": CHANNEL_MODERATION,
        "CHANNEL_SUGGESTIONS": CHANNEL_SUGGESTIONS,
        "WEB_TOKEN": WEB_TOKEN,
        "MEMBER_ROLE": MEMBER_ROLE,
        "SENTRY_SDK": SENTRY_SDK,
    }
)
