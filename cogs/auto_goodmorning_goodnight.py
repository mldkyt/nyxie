from datetime import datetime

from aiohttp import ClientSession
from discord import Cog, Bot, Interaction
from discord.ext.tasks import loop
from discord.ui import Modal, InputText, View, button, Button

from constants import OWNER, FEDI_INSTANCE, FEDI_USER_ID, FEDI_TOKEN

DEBUG_NIGHT = False
DEBUG_MORNING = False


class WriteGoodNightMessage(Modal):
    def __init__(self):
        super().__init__(title="Good Night")

        self.post = InputText(label="Message", placeholder="nini fedi :3", required=True, min_length=1)
        self.add_item(self.post)

    async def callback(self, interaction: Interaction):
        async with ClientSession() as session:
            async with session.post(f"https://{FEDI_INSTANCE}/api/notes/create", json={
                'text': self.post.value,
                'visibility': 'specified',
                'visibleUserIds': [
                    FEDI_USER_ID
                ]
            }, headers={
                'Authorization': f'Bearer {FEDI_TOKEN}'
            }) as req:
                if not req.ok:
                    message = await req.text()
                    await interaction.respond(f"Good night message failed with code {req.status}: {req.reason}\n```{message}```", ephemeral=True)
                    return

        await interaction.respond("OK", ephemeral=True)

class WriteGoodMorningMessage(Modal):
    def __init__(self):
        super().__init__(title="Good Morning")

        self.post = InputText(label="Message", placeholder="morning fedi :3", required=True)
        self.add_item(self.post)

    async def callback(self, interaction: Interaction):
        async with ClientSession() as session:
            async with session.post(f"https://{FEDI_INSTANCE}/api/notes/create", json={
                'text': self.post.value,
                'visibility': 'specified',
                'visibleUserIds': [
                    FEDI_USER_ID
                ]
            }, headers={
                'Authorization': f'Bearer {FEDI_TOKEN}'
            }) as req:
                if not req.ok:
                    message = await req.text()
                    await interaction.respond(f"Good morning message failed with code {req.status}: {req.reason}\n```{message}```", ephemeral=True)
                    return

        await interaction.respond("OK", ephemeral=True)

class ViewGoodMorning(View):
    def __init__(self):
        super().__init__()

    @button(label="Send good morning")
    async def good_morning(self, btn: Button, inter: Interaction):
        await inter.response.send_modal(WriteGoodMorningMessage())

class ViewGoodNight(View):
    def __init__(self):
        super().__init__()

    @button(label="Send good night")
    async def good_morning(self, btn: Button, inter: Interaction):
        await inter.response.send_modal(WriteGoodNightMessage())


class AutoGoodMorningGoodNight(Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        self.check_time.start()

    @loop(minutes=1)
    async def check_time(self):
        now = datetime.now()

        owner = self.bot.get_user(int(OWNER))

        # Night
        if (now.hour == 20 and now.minute == 0) or DEBUG_NIGHT:
            await owner.send("Say a good night to fedi!", view=ViewGoodNight())

        # Morning
        if (now.hour == 6 and now.minute == 0) or DEBUG_MORNING:
            await owner.send("Say a good meowning to fedi :3", view=ViewGoodMorning())

