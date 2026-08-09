import os.path
from asyncio import gather
from datetime import datetime
from random import choice, randint

import html2text
from discord import (
    ApplicationContext,
    Bot,
    ButtonStyle,
    Cog,
    Color,
    Embed,
    EmbedField,
    EmbedFooter,
    File,
    Guild,
    Interaction,
    TextChannel,
    default_permissions,
    slash_command,
)
from discord.ext.tasks import loop
from discord.ui import Button, View, button
from sqlalchemy import delete, select, update

from constants import (
    CHANNEL_MEOW,
    CHANNEL_YAOI,
    CHANNEL_YURI,
    GUILD,
    VERSION,
)
from database import alt_text_suggestions, engine, yaoi_db, yuri_db
from util.yaoibot import YaoiBot
from util.yuri_util import (
    get_some_yaoi,
    get_some_yuri,
    respond_with_next_non_alted_content,
    respond_with_next_yuri,
)
from util.yuribot import YuriBot

DEBUG = False

yuribot = None
if os.path.exists("data/yuribot_usercred.secret"):
    yuribot = YuriBot()

yaoibot = None
if os.path.exists("data/yaoibot_usercred.secret"):
    yaoibot = YaoiBot()


async def post_yuri(bot: Bot):
    guild = bot.get_guild(int(GUILD))
    if not isinstance(guild, Guild):
        return

    chan = guild.get_channel(int(CHANNEL_YURI))
    if not isinstance(chan, TextChannel):
        return

    with engine.begin() as c:
        yuri_filename, yuri_source, cw, alt = get_some_yuri(c)

    if not yuri_filename:
        return
    if not cw:
        cw = ""

    if len(cw.strip()) == 0:
        embed = Embed(
            title="Yuri :3",
            image=f"attachment://{yuri_filename.split('/')[-1]}",
            footer=EmbedFooter(text=f"mldmon {VERSION}"),
            description=f"[source]({yuri_source})",
            color=Color.nitro_pink(),
        )
    else:
        embed = Embed(
            title="Yuri :3",
            footer=EmbedFooter(text=f"mldmon {VERSION}"),
            description=f"[source]({yuri_source})",
            color=Color.nitro_pink(),
        )

    await chan.send(
        embed=embed,
        file=File(yuri_filename, spoiler=len(cw.strip()) > 0, description=alt),
    )

    if yuribot is not None:
        yuribot.also_post_on_fedi(yuri_filename, yuri_source, cw)


async def post_yaoi(bot: Bot):
    guild = bot.get_guild(int(GUILD))
    if not isinstance(guild, Guild):
        return
    chan = guild.get_channel(int(CHANNEL_YAOI))
    if not isinstance(chan, TextChannel):
        return

    with engine.begin() as c:
        yaoi_filename, yaoi_source, cw, alt = get_some_yaoi(c)

    if not yaoi_filename:
        return

    if not cw:
        cw = ""

    if len(cw.strip()) == 0:
        embed = Embed(
            title="Yaoi :3",
            image=f"attachment://{yaoi_filename.split('/')[-1]}",
            description=f"[source]({yaoi_source})",
            color=Color.nitro_pink(),
        )
    else:
        embed = Embed(
            title="Yaoi :3",
            description=f"[source]({yaoi_source})",
            color=Color.nitro_pink(),
        )

    await chan.send(
        embed=embed,
        file=File(yaoi_filename, spoiler=len(cw.strip()) > 0, description=alt),
    )

    if yaoibot is not None:
        yaoibot.also_post_on_fedi(yaoi_filename, yaoi_source, cw)


def generate_meow():
    meow = choice(["meow", "nya", "mraow", "mwrmmwra"])

    if meow == "nya":
        return "ny" + randint(1, 8) * "a"
    elif meow == "mwrmmwra":
        meow = "mr"
        for i in range(randint(4, 12)):
            meow += choice(["a", "w", "r"])

        return meow

    return meow


async def post_meow(bot: Bot):
    guild = bot.get_guild(int(GUILD))
    if not isinstance(guild, Guild):
        return
    chan = guild.get_channel(int(CHANNEL_MEOW))
    if not isinstance(chan, TextChannel):
        return

    await chan.send(generate_meow() + " :3")


class ApproveAltText(View):
    def __init__(self, id: int):
        super().__init__()
        self.alt_text_id = id

    @button(label="Approve", style=ButtonStyle.green)
    async def approve(self, button: Button, interaction: Interaction):
        with engine.begin() as c:
            alt_text = c.execute(
                select(
                    alt_text_suggestions.c.fid,
                    alt_text_suggestions.c.status_id,
                    alt_text_suggestions.c.type,
                    alt_text_suggestions.c.alt,
                    alt_text_suggestions.c.acct,
                ).where(alt_text_suggestions.c.id == self.alt_text_id)
            ).fetchone()

        if alt_text is None:
            await interaction.respond("what", ephemeral=True)
            return

        # Update status
        if yuribot is not None:
            status = yuribot.mastodon_yuribot.status(alt_text[1])
            yuribot.mastodon_yuribot.status_update(
                status,
                html2text.html2text(status.content),
                media_attributes=[
                    yuribot.mastodon_yuribot.generate_media_edit_attributes(
                        status.media_attachments[0].id,
                        description=f"{alt_text[3]}\n\nAlt text suggested by {alt_text[4]} and approved by mldkyt.",
                    )
                ],
            )

        # Update the record
        with engine.begin() as c:
            if alt_text[2] == "yuri":
                c.execute(
                    update(yuri_db)
                    .values(
                        alt=f"{alt_text[3]}\n\nAlt text suggested by {alt_text[4]} and approved by mldkyt."
                    )
                    .where(yuri_db.c.id == alt_text[0])
                )
            elif alt_text[2] == "yaoi":
                c.execute(
                    update(yaoi_db)
                    .values(
                        alt=f"{alt_text[3]}\n\nAlt text suggested by {alt_text[4]} and approved by mldkyt."
                    )
                    .where(yaoi_db.c.id == alt_text[0])
                )

            # Delete other suggestions
            c.execute(
                delete(alt_text_suggestions).where(
                    (alt_text_suggestions.c.fid == alt_text[0])
                    & (alt_text_suggestions.c.type == alt_text[2])
                )
            ).fetchone()

        self.disable_all_items()
        await interaction.edit(view=self)

    @button(label="Decline", style=ButtonStyle.red)
    async def decline(self, button: Button, interaction: Interaction):
        with engine.begin() as c:
            alt_text = c.execute(
                select(
                    alt_text_suggestions.c.id,
                ).where(alt_text_suggestions.c.id == self.alt_text_id)
            ).fetchone()

            if alt_text is None:
                await interaction.respond("what", ephemeral=True)
                return

            c.execute(
                delete(
                    alt_text_suggestions,
                ).where(alt_text_suggestions.c.id == self.alt_text_id)
            ).fetchone()

        self.disable_all_items()
        await interaction.edit(view=self)


class ChannelPosting(Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        self.periodic_run.start()

    @loop(minutes=1)
    async def periodic_run(self):
        now = datetime.now()

        if (now.hour == 0 and now.minute == 0) or DEBUG:
            await post_meow(self.bot)
        if now.minute == 0 or DEBUG:
            await gather(post_yuri(self.bot), post_yaoi(self.bot))

    @slash_command(name="approve_content")
    @default_permissions(manage_guild=True)
    async def manage_content(self, ctx: ApplicationContext, reapprove: bool = False):
        if not await respond_with_next_yuri(ctx.interaction, reapprove=reapprove):
            await ctx.respond("All done!", ephemeral=True)

    @slash_command(name="add_alt_texts_to_content")
    @default_permissions(manage_guild=True)
    async def add_alt_texts(self, ctx: ApplicationContext):
        if not await respond_with_next_non_alted_content(ctx.interaction):
            await ctx.respond("All done!", ephemeral=True)

    @slash_command(name="approve_alt_text")
    @default_permissions(manage_guild=True)
    async def approve_alt_text(self, ctx: ApplicationContext):
        with engine.begin() as c:
            post = c.execute(
                select(
                    alt_text_suggestions.c.id,
                    alt_text_suggestions.c.type,
                    alt_text_suggestions.c.alt,
                    alt_text_suggestions.c.acct,
                    alt_text_suggestions.c.fid,
                )
            ).fetchone()
            if post is None:
                await ctx.respond("No alt text posts to approve", ephemeral=True)
                return

            source = None
            if post[1] == "yaoi":
                source = c.execute(
                    select(yaoi_db).where(yaoi_db.c.id == post[4])
                ).fetchone()
            elif post[1] == "yuri":
                source = c.execute(
                    select(yuri_db).where(yuri_db.c.id == post[4])
                ).fetchone()

            if source is None:
                c.execute(
                    delete(alt_text_suggestions).where(
                        alt_text_suggestions.c.id == post[0]
                    )
                )
                await ctx.respond("Please re-run this command...", ephemeral=True)
                return

            source = source[0]

        embed = Embed(
            fields=[
                EmbedField("source", source),
                EmbedField("alt text", post[2]),
                EmbedField("suggested by", post[3]),
            ]
        )

        await ctx.respond(
            "Please approve the following alt text:",
            embed=embed,
            view=ApproveAltText(post[0]),
        )


def setup(bot: Bot):
    bot.add_cog(ChannelPosting(bot))
