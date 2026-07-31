import os

from dotenv import load_dotenv

from logger import lunamon_logger

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

FORGEJO_INSTANCE = os.getenv("FORGEJO_INSTANCE")
FORGEJO_TOKEN = os.getenv("FORGEJO_TOKEN")
FORGEJO_OWNER = os.getenv("FORGEJO_OWNER")
FORGEJO_PROJECT = os.getenv("FORGEJO_PROJECT")

DEEPL_API_KEY = os.getenv("DEEPL_API_KEY")
WEB_TOKEN = os.getenv("WEB_TOKEN")

MCAPTCHA_DOMAIN = os.getenv("MCAPTCHA_DOMAIN")
MCAPTCHA_SITEKEY = os.getenv("MCAPTCHA_SITEKEY")
MCAPTCHA_SECRET = os.getenv("MCAPTCHA_SECRET")

MEMBER_ROLE = os.getenv("MEMBER_ROLE")

SENTRY_SDK = os.getenv("SENTRY_SDK")

def validate_values(l: dict[str, str | None]):
    for k, v in l.items():
        if v is None:
            lunamon_logger.warning(f"CONSTANTS: The constant value for {k} is NOT set!")


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
        "FORGEJO_INSTANCE": FORGEJO_INSTANCE,
        "FORGEJO_TOKEN": FORGEJO_TOKEN,
        "FORGEJO_OWNER": FORGEJO_OWNER,
        "FORGEJO_PROJECT": FORGEJO_PROJECT,
        "DEEPL_API_KEY": DEEPL_API_KEY,
        "WEB_TOKEN": WEB_TOKEN,
        "MCAPTCHA_DOMAIN": MCAPTCHA_DOMAIN,
        "MCAPTCHA_SITEKEY": MCAPTCHA_SITEKEY,
        "MCAPTCHA_SECRET": MCAPTCHA_SECRET,
        "MEMBER_ROLE": MEMBER_ROLE,
        "SENTRY_SDK": SENTRY_SDK,
    }
)
