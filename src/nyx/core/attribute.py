from nyx.core.serializable import Serializable
from nyx.utils import file_fn


class Attribute(Serializable):

    def __init__(self, node, name: str, value=None) -> None:
        super().__init__()
        self.node = node
        self.__name = name
        self.__value = value

    def __repr__(self) -> str:
        return f"Attribute {self.name}: {self.value}"

    def __eq__(self, other_attr):
        # type: (Attribute) -> bool
        if not isinstance(other_attr, Attribute):
            raise TypeError("Can't compare with not attribute.")
        return all(
            [
                self.node is other_attr.node,
                self.name == other_attr.name,
                self.value == other_attr.value
            ]
        )

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
        value = self.value if file_fn.is_jsonable(self.value) else None
        new_data = {"name": self.name,
                    "value": value}
        data.update(new_data)
        return data

    def deserialize(self, data: dict, hashmap: dict = None, restore_id=False):
        super().deserialize(data, hashmap, restore_id)
        self.set_name(data.get("name", self.name))
        self.set_value(data.get("value", self.value))
