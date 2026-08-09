import os
import random

from discord import ButtonStyle, Embed, EmbedField, File, Interaction
from discord.ui import Button, InputText, Modal, View, button
from sqlalchemy import Connection, delete, desc, select, update
from sqlalchemy.sql.functions import max

from database import alt_text_suggestions, cw_suggestions, engine, yaoi_db, yuri_db
from util.yuribot import yuribot


async def respond_with_next_yuri(ctx: Interaction, reapprove: bool = False) -> bool:
    with engine.begin() as c:
        if reapprove:
            c.execute(update(yuri_db).values(approved=False))
            c.execute(update(yaoi_db).values(approved=False))

        yuri = c.execute(
            select(yuri_db.c.id, yuri_db.c.filename).where(yuri_db.c.approved == False)
        ).fetchone()

        if yuri is not None:
            await ctx.respond(
                view=YuriApproval("yuri", yuri[0]),
                embed=Embed(
                    title="Approve this yuri",
                    image=f"attachment://{yuri[1].split('/')[-1]}",
                ),
                file=File(yuri[1]),
                ephemeral=True,
            )
            return True

        yaoi = c.execute(
            select(yaoi_db.c.id, yaoi_db.c.filename).where(yaoi_db.c.approved == False)
        ).fetchone()

        if yaoi is not None:
            await ctx.respond(
                view=YuriApproval("yaoi", yaoi[0]),
                embed=Embed(
                    title="Approve this yaoi",
                    image=f"attachment://{yaoi[1].split('/')[-1]}",
                ),
                file=File(yaoi[1]),
                ephemeral=True,
            )
            return True

    return False


async def respond_with_next_non_alted_content(ctx: Interaction) -> bool:
    with engine.begin() as c:
        yuri = c.execute(
            select(yuri_db.c.id, yuri_db.c.filename).where(yuri_db.c.alt == "")
        ).fetchone()

        if yuri is not None:
            await ctx.respond(
                view=YuriAskForAltText("yuri", yuri[0]),
                embed=Embed(
                    title="Add alt text to this yuri using the button below",
                    image=f"attachment://{yuri[1].split('/')[-1]}",
                ),
                file=File(yuri[1]),
                ephemeral=True,
            )
            return True

        yaoi = c.execute(
            select(yaoi_db.c.id, yaoi_db.c.filename).where(yaoi_db.c.approved == False)
        ).fetchone()

        if yaoi is not None:
            await ctx.respond(
                view=YuriAskForAltText("yaoi", yaoi[0]),
                embed=Embed(
                    title="Add alt text to this yaoi using the button below",
                    image=f"attachment://{yaoi[1].split('/')[-1]}",
                ),
                file=File(yaoi[1]),
                ephemeral=True,
            )
            return True

    return False


async def respond_with_thing_to_approve(ctx: Interaction) -> bool:
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
        if post is not None:
            source = None
            if post[1] == "yaoi":
                source = c.execute(
                    select(yaoi_db.c.source).where(yaoi_db.c.id == post[4])
                ).fetchone()
            elif post[1] == "yuri":
                source = c.execute(
                    select(yuri_db.c.source).where(yuri_db.c.id == post[4])
                ).fetchone()

            if source is None:
                c.execute(
                    delete(alt_text_suggestions).where(
                        alt_text_suggestions.c.id == post[0]
                    )
                )
                return await respond_with_thing_to_approve(ctx)

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
            return True

        cw = c.execute(
            select(
                cw_suggestions.c.id,
                cw_suggestions.c.type,
                cw_suggestions.c.cw,
                cw_suggestions.c.fid,
            )
        ).fetchone()
        if cw is not None:
            source = None
            if cw[1] == "yaoi":
                source = c.execute(
                    select(yaoi_db.c.source).where(yaoi_db.c.id == cw[3])
                ).fetchone()
            elif cw[1] == "yuri":
                source = c.execute(
                    select(yuri_db.c.source).where(yuri_db.c.id == cw[3])
                ).fetchone()

            if source is None:
                c.execute(delete(cw_suggestions).where(cw_suggestions.c.id == cw[0]))
                return await respond_with_thing_to_approve(ctx)

            source = source[0]

            embed = Embed(
                fields=[
                    EmbedField("source", source),
                    EmbedField("CW", cw[2]),
                ]
            )

            await ctx.respond(
                "Please approve the following CW:",
                embed=embed,
                view=ApproveCW(cw[0]),
            )

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

        await interaction.respond(
            "CW " + ("updated" if len(new_cw) > 0 else "removed"), ephemeral=True
        )


class YuriAltTextModal(Modal):
    def __init__(self, type: str, id: int):
        super().__init__(title=f"Add alt text to this {type}")
        self.type = type
        self.content_id = id
        self.alt = InputText(
            label="Alt text", placeholder="2 girls making out sloppy style no socks"
        )
        self.add_item(self.alt)

    async def callback(self, interaction: Interaction):
        new_alt = self.alt.value or ""

        with engine.begin() as c:
            if self.type == "yuri":
                c.execute(
                    update(yuri_db)
                    .where(yuri_db.c.id == self.content_id)
                    .values(alt=new_alt)
                )
            elif self.type == "yaoi":
                c.execute(
                    update(yaoi_db)
                    .where(yaoi_db.c.id == self.content_id)
                    .values(alt=new_alt)
                )

        if not await respond_with_next_non_alted_content(interaction):
            await interaction.respond("All done!", ephemeral=True)


class YuriAskForAltText(View):
    def __init__(self, type: str, content_id: int):
        super().__init__()

        self.type = type
        self.content_id = content_id

    @button(label="Set alt", style=ButtonStyle.secondary)
    async def set_alt(self, button: Button, interaction: Interaction):
        await interaction.response.send_modal(
            YuriAltTextModal(self.type, self.content_id)
        )


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
                    select(yuri_db.c.filename).where(yuri_db.c.id == self.content_id)
                ).fetchone()

                if yuri is None:
                    return

                os.remove(yuri[0])

                c.execute(delete(yuri_db).where(yuri_db.c.id == self.content_id))
            elif self.type == "yaoi":
                yaoi = c.execute(
                    select(yaoi_db.c.filename).where(yaoi_db.c.id == self.content_id)
                ).fetchone()

                if yaoi is None:
                    return

                os.remove(yaoi[0])

                c.execute(delete(yaoi_db).where(yaoi_db.c.id == self.content_id))

        if not await respond_with_next_yuri(ctx):
            await ctx.respond("All done!", ephemeral=True)

    @button(label="Set CW", style=ButtonStyle.secondary)
    async def set_cw(self, button: Button, interaction: Interaction):
        await interaction.response.send_modal(YuriCWModal(self.type, self.content_id))

    @button(label="Set alt", style=ButtonStyle.secondary)
    async def set_alt(self, button: Button, interaction: Interaction):
        await interaction.response.send_modal(
            YuriAltTextModal(self.type, self.content_id)
        )


def get_some_yuri(
    conn: Connection,
) -> tuple[str | None, str | None, str | None, str | None]:
    """Returns relative path to yuri and source link and ticks it"""

    top_priority = conn.execute(
        select(max(yuri_db.c.priority)).where(yuri_db.c.approved == True)
    ).fetchone()
    if not top_priority:
        return None, None, None, None

    top_priority = top_priority[0]

    yuri = conn.execute(
        select(
            yuri_db.c.id,
            yuri_db.c.filename,
            yuri_db.c.source,
            yuri_db.c.alt,
            yuri_db.c.alt,
        )
        .where(yuri_db.c.priority == top_priority)
        .where(yuri_db.c.approved == True)
    ).fetchall()

    yuri = random.choice(yuri)

    conn.execute(
        update(yuri_db)
        .where(yuri_db.c.id == yuri[0])
        .values(priority=yuri_db.c.priority - 1)
    )

    return yuri[1], yuri[2], yuri[3], yuri[4]


def get_some_yaoi(
    conn: Connection,
) -> tuple[str | None, str | None, str | None, str | None]:
    """Returns relative path to yaoi and source link and ticks it"""

    top_priority = conn.execute(
        select(max(yaoi_db.c.priority)).where(yaoi_db.c.approved == True)
    ).fetchone()
    if not top_priority:
        return None, None, None, None

    top_priority = top_priority[0]

    yaoi = conn.execute(
        select(
            yaoi_db.c.id,
            yaoi_db.c.filename,
            yaoi_db.c.source,
            yaoi_db.c.alt,
            yaoi_db.c.alt,
        )
        .where(yaoi_db.c.priority == top_priority)
        .where(yaoi_db.c.approved == True)
    ).fetchall()

    yaoi = random.choice(yaoi)

    conn.execute(
        update(yaoi_db)
        .where(yaoi_db.c.id == yaoi[0])
        .values(priority=yaoi_db.c.priority - 1)
    )

    return yaoi[1], yaoi[2], yaoi[3], yaoi[4]


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
                status.content,
                spoiler_text=status.spoiler_text,
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
            )

        self.disable_all_items()
        await interaction.edit(view=self)

    @button(label="Decline", style=ButtonStyle.red)
    async def decline(self, button: Button, interaction: Interaction):
        with engine.begin() as c:
            c.execute(
                delete(
                    alt_text_suggestions,
                ).where(alt_text_suggestions.c.id == self.alt_text_id)
            )

        self.disable_all_items()


class ApproveCW(View):
    def __init__(self, id: int):
        super().__init__()
        self.cw_id = id

    @button(label="Approve", style=ButtonStyle.green)
    async def approve(self, button: Button, interaction: Interaction):
        with engine.begin() as c:
            cw = c.execute(
                select(
                    cw_suggestions.c.fid,
                    cw_suggestions.c.status_id,
                    cw_suggestions.c.type,
                    cw_suggestions.c.cw,
                ).where(cw_suggestions.c.id == self.cw_id)
            ).fetchone()

        if cw is None:
            await interaction.respond("what", ephemeral=True)
            return

        # Update status
        if yuribot is not None:
            status = yuribot.mastodon_yuribot.status(cw[1])
            yuribot.mastodon_yuribot.status_update(
                status,
                status.content,
                spoiler_text=cw[3],
                media_attributes=[
                    yuribot.mastodon_yuribot.generate_media_edit_attributes(
                        id=status.media_attachments[0].id,
                        description=status.media_attachments[0].description,
                    )
                ],
            )

        # Update the record
        with engine.begin() as c:
            if cw[2] == "yuri":
                c.execute(update(yuri_db).values(cw=cw[3]).where(yuri_db.c.id == cw[0]))
            elif cw[2] == "yaoi":
                c.execute(update(yaoi_db).values(cw=cw[3]).where(yaoi_db.c.id == cw[0]))

            # Delete other suggestions
            c.execute(
                delete(cw_suggestions).where(
                    (cw_suggestions.c.fid == cw[0]) & (cw_suggestions.c.type == cw[2])
                )
            )

        self.disable_all_items()
        await interaction.edit(view=self)

    @button(label="Decline", style=ButtonStyle.red)
    async def decline(self, button: Button, interaction: Interaction):
        with engine.begin() as c:
            c.execute(
                delete(
                    cw_suggestions,
                ).where(cw_suggestions.c.id == self.cw_id)
            )

        self.disable_all_items()
        await interaction.edit(view=self)
