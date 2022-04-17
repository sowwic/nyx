import typing
from collections import OrderedDict
from nyx.core.serializable import Serializable
from nyx.utils import file_fn
if typing.TYPE_CHECKING:
    from nyx.core import Node


class Attribute(Serializable):

    def __init__(self, node: "Node", name: str, value=None) -> None:
        super().__init__()
        self.node = node
        self.__name = name
        self.__value = value
        self.__writable = True
        self.__readable = True

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

    @property
    def writable(self):
        return self.__writable

    @property
    def readable(self):
        return self.__readable

    def get_value(self):
        return self.value

    def set_value(self, value):
        self.__value = value

    def get_name(self):
        return self.name

    def set_name(self, name: str):
        self.__name = name

    def get_writable(self):
        return self.writable

    def set_writable(self, state: bool):
        self.__writable = state

    def get_readable(self):
        return self.readable

    def set_readable(self, state: bool):
        self.__readable = state

    def serialize(self) -> OrderedDict:
        data = super().serialize()
        value = self.value if file_fn.is_jsonable(self.value) else None
        new_data = {"name": self.name,
                    "value": value,
                    "writable": self.writable,
                    "readable": self.readable}
        data.update(new_data)
        return data

    def deserialize(self, data: dict, hashmap: dict = None, restore_id=False):
        super().deserialize(data, hashmap, restore_id)
        self.set_name(data.get("name", self.name))
        self.set_value(data.get("value", self.value))
        self.set_writable(data.get("writable", True))
        self.set_readable(data.get("readable", True))

    def resolve(self):
        pass
