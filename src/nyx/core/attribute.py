import typing
from collections import OrderedDict

from nyx import get_main_logger
from nyx.core.serializable import Serializable
from nyx.utils import file_fn
if typing.TYPE_CHECKING:
    from nyx.core import Node


LOGGER = get_main_logger()


class Attribute(Serializable):

    def __init__(self, node: "Node", value=None) -> None:
        super().__init__()
        self.node = node
        self.__value = value
        self.__cached_value = None

    def __repr__(self) -> str:
        return f"Attribute ({self.name}: {self.value})"

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
        all_node_attribs = self.node.attribs
        for name, attr in all_node_attribs.items():
            if self is attr:
                return name

        LOGGER.error(f"Failed to get name for attribute of {self.node}")
        raise ValueError

    def get_value(self):
        return self.value

    def set_value(self, value):
        self.__value = value

    def get_name(self):
        return self.name

    def serialize(self) -> OrderedDict:
        data = super().serialize()
        value = self.value if file_fn.is_jsonable(self.value) else None
        new_data = {"name": self.name,
                    "value": value}
        data.update(new_data)
        return data

    def deserialize(self, data: dict, hashmap: dict = None, restore_id=False):
        super().deserialize(data, hashmap, restore_id)
        self.set_value(data.get("value", self.value))

    def resolve(self):
        pass
