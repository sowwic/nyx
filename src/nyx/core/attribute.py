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
        self.__node = node
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
    def node(self):
        return self.__node

    @property
    def value(self):
        """Raw attribute value.

        Returns:
            typing.Any: stored value
        """
        return self.__value

    @property
    def cached_value(self):
        """Cached value.

        Returns:
            typing.Any: stored cached value
        """
        return self.__cached_value

    @property
    def name(self):
        """Attribute name.

        Raises:
            ValueError: error when getting attr from node.

        Returns:
            str: name
        """
        all_node_attribs = self.node.attribs
        for name, attr in all_node_attribs.items():
            if self is attr:
                return name

        LOGGER.error(f"Failed to get name for attribute of {self.node}")
        raise ValueError

    def get(self, cached=False):
        """Get attribute value

        Args:
            cached (bool, optional): get cached value instead. Defaults to False.

        Returns:
            typing.Any: value.
        """
        return self.value if not cached else self.cached_value

    def set(self, value):
        """Set raw attribute value"""
        self.__value = value

    def push(self, value):
        """Push given value to cache"""
        self.__cached_value = value

    def clear_cache(self):
        """Set cache value to None."""
        self.__cached_value = None

    def is_cached(self) -> bool:
        """Is value equal to cached value

        Returns:
            bool: cached
        """
        return self.value == self.cached_value

    def same_scope_with(self, other_attr: "Attribute"):
        """Check if this and other attribute are in the same scope.

        Args:
            other_attr (Attribute): attribute to compare to

        Returns:
            bool: in same scope.
        """
        return self.node.scope == other_attr.node.scope

    def cache_current_value(self):
        """Push current value to cache."""
        self.push(self.value)

    def get_name(self):
        """Get attribute name.

        Returns:
            str: attribute name.
        """
        return self.name

    def serialize(self) -> OrderedDict:
        data = super().serialize()
        value = self.value if file_fn.is_jsonable(self.value) else None
        new_data = {"name": self.name,
                    "value": value}
        data.update(new_data)
        return data

    def deserialize(self, data: dict, hashmap: dict, restore_id=False):
        super().deserialize(data, hashmap, restore_id)
        self.set(data.get("value", self.value))

    def resolve(self):
        pass
