from nyx.core.serializable import Serializable


class Attribute(Serializable):
    def __init__(self, node, name: str, value=None) -> None:
        self.node = node
        self.__name = name
        self.__value = value

    @property
    def value(self):
        return self.__value

    @property
    def name(self):
        return self.__name

    def set_value(self, value):
        self.__value = value

    def set_name(self, name: str):
        self.__name = name

    def serialize(self) -> dict:
        data = super().serialize()
        new_data = {"name": self.name,
                    "value": self.value}
        data.update(new_data)
        return data

    def deserialize(self, data: dict, hashmap: dict = None, restore_id=False):
        super().deserialize(data, hashmap, restore_id)
        self.set_name(data.get("name"), self.name)
        self.set_value(data.get("value"), self.value)
