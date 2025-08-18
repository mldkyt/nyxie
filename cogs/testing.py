import discord
import word2number.w2n

from constants import CHANNEL_TESTING


class Testing(discord.Cog):
    def __init__(self):
        super().__init__()

    @discord.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if msg.author.bot:
            return

        if msg.channel.id != int(CHANNEL_TESTING):
            return

        try:
            a = word2number.w2n.word_to_num(msg.content)
            await msg.reply(a)
        except Exception as e:
            await msg.reply(str(e))
