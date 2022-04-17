import uuid


class Serializable:
    def __init__(self) -> None:
        self.uuid = str(uuid.uuid4())

    def serialize(self) -> dict:
        return {"uuid": self.uuid}

    def deserialize(self, data: dict, hashmap: dict = None, restore_id=False):
        if restore_id:
            self.uuid = data["uuid"]
        hashmap[data["uuid"]] = self
