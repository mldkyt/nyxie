from discord import Embed

class DM:
    dms_to_send: list[tuple[int, str | Embed]] = []

    def add_dm_to_send(self, user: int, message: str | Embed):
        self.dms_to_send.append((user, message))

    def get_message_to_send(self) -> tuple[int, str | Embed] | None:
        if len(self.dms_to_send) == 0:
            return None
        dm = self.dms_to_send[0]
        self.dms_to_send.remove(dm)
        return dm

dm_cache = DM()
