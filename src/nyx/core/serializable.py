from collections import OrderedDict
import uuid


class Serializable:
    def __init__(self) -> None:
        self.uuid = str(uuid.uuid4())

    def serialize(self) -> OrderedDict:
        data = OrderedDict()
        data["uuid"] = self.uuid
        return data

    def deserialize(self, data: OrderedDict, hashmap: dict = None, restore_id=False):
        if restore_id:
            self.uuid = data["uuid"]
        hashmap[data["uuid"]] = self
