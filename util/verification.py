import datetime

from discord import Guild, ButtonStyle
from discord.ui import View, ViewItem, Button
from discord.ui.view import V

from constants import MEMBER_ROLE


async def unverified_members(guild: Guild):
    member_role = await guild.fetch_role(int(MEMBER_ROLE))

    async for member in guild.fetch_members(limit=None):
        if member.bot:
            continue
        if member.guild_permissions.manage_guild or member.guild_permissions.kick_members or member.guild_permissions.ban_members or member.guild_permissions.mute_members:
            continue
        if member_role in member.roles:
            continue
        if member.joined_at is not None and (datetime.datetime.now(datetime.UTC) - member.joined_at) < datetime.timedelta(days=7):
            continue

        yield member


class RejoinView(View):
    def __init__(self):
        super().__init__()

        self.add_item(
            Button(url="https://discord.gg/uTWjgy2E4v", label="Rejoin the server", style=ButtonStyle.url)
        )
