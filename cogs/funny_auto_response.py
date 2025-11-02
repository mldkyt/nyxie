import logging
import random
import re

import discord
from discord import Bot

from constants import GUILD, CHANNEL_COUNTING

ai_logger = logging.getLogger("ai")

def handle_colon_three(message: discord.Message):
    # count :3 in message
    count = 0
    for i in re.finditer(r":(3+)", message.content.lower()):
        count = count + len(i[1])

    if count == 0:
        return ""

    return ":3 " * count

def generate_meow():
    meow = random.choice(["meow", "nya", "mraow", "mwrmmwra"])

    if meow == "nya":
        return "ny" + random.randint(1, 8) * "a"
    elif meow == "mwrmmwra":
        meow = "mr"
        for i in range(random.randint(4, 12)):
            meow += random.choice(["a", "w", "r"])

        return meow

    return meow


def handle_meow(message: discord.Message):
    # count meows
    count = 0

    for i in message.content.split(" "):
        count += len(re.findall(r"(^m[mraeowp]{3,}$|^nya+$)", i.lower()))

    if count == 0:
        return ""

    return " ".join([generate_meow() for _ in range(count)]) + " :3"


def generate_woof():
    a = random.choice([0, 1])

    if a == 0:
        is_a = random.choice([0, 1])

        return ("a" if is_a else "") + "wru" + "f" * random.randint(1, 3)
    elif a == 1:
        return "woof"
    else:
        return "waf"


def handle_woof(message: discord.Message):
    # count woofs
    count = 0

    for i in message.content.split(" "):
        count += len(re.findall(r"(^[awruf]?[wrouf]+)$", i.lower()))

    if count == 0:
        return ""

    return " ".join([generate_woof() for _ in range(count)])


def handle_waf(message: discord.Message):
    count = 0

    for i in message.content.split(" "):
        if i.lower() == "waf":
            count += 1

    if count == 0:
        return ""

    return " ".join(["waf" for _ in range(count)])


def handle_owo(message: discord.Message):
    # count OwOs and UwUs
    count = len(re.findall(r"([ou>]w[<ou])", message.content.lower()))

    if count == 0:
        return ""

    return " ".join(random.choices(["OwO", "owo", "UwU", "uwu", ">w<"], k=count)) + " :3"


def handle_gex(message: discord.Message):
    count_say_gex = len(re.findall(r"say gex", message.content.lower()))
    count_sesbian_lex = len(re.findall(r"sesbian lex", message.content.lower()))

    resp = "say gex " * count_say_gex
    resp += "sesbian lex " * count_sesbian_lex
    return resp.strip()

def handle_awawa(message: discord.Message):
    count_awawa = 0

    for i in message.content.split(" "):
        if i.startswith("awa"):
            count_awawa += (len(i) - 3) // 2

    resp = "awa" + "wa" * count_awawa

    if count_awawa == 0:
        return ""

    return resp.strip()


class FunnyAutoResponse(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            if message.guild is None:
                return

            if message.author.bot:
                return

            if message.guild.id != int(GUILD):
                return

            if message.channel.id == int(CHANNEL_COUNTING):
                return

            if "so true" in message.content or "so real" in message.content:
                await message.reply(file=discord.File("rom/sotruebestie.gif"))

            message_reply = " ".join([
                handle_meow(message),
                handle_colon_three(message),
                handle_owo(message),
                handle_gex(message),
                handle_awawa(message),
                handle_woof(message),
                handle_waf(message)
            ])

            message_reply = message_reply.replace("  ", " ")

            if len(message_reply.strip()) > 0:
                await message.channel.send(message_reply)
        except Exception as e:
            ai_logger.exception("An error occurred:")

def setup(bot: Bot):
    bot.add_cog(FunnyAutoResponse(bot))
