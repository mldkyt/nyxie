from discord import Embed
from discord.ui import DesignerView

class DM:
    dms_to_send: list[tuple[int, str | Embed | DesignerView]] = []

    def add_dm_to_send(self, user: int, message: str | Embed | DesignerView):
        self.dms_to_send.append((user, message))

    def get_message_to_send(self) -> tuple[int, str | Embed | DesignerView] | None:
        if len(self.dms_to_send) == 0:
            return None
        dm = self.dms_to_send[0]
        self.dms_to_send.remove(dm)
        return dm

dm_cache = DM()
