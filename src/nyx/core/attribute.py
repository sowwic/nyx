import typing
import pathlib
from collections import OrderedDict

from nyx import get_main_logger
from nyx.core.serializable import Serializable
from nyx.core import nyx_exceptions
from nyx.utils import file_fn
if typing.TYPE_CHECKING:
    from nyx.core import Node


LOGGER = get_main_logger()


class Attribute(Serializable):

    def __init__(self, node: "Node", value=None) -> None:
        super().__init__()
        self.__node = node
        self.__value = value
        self.__resolved = None
        self.__cached_value = None

    def __repr__(self) -> str:
        return f"Attribute {self.name} (raw: {self.value}, resolved: {self.resolved_value}, cached: {self.cached_value})"

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
    def stage(self):
        return self.node.stage

    @property
    def value(self):
        """Raw attribute value.

        Returns:
            typing.Any: stored value
        """
        return self.__value

    @property
    def resolved_value(self):
        """Cached value.

        Returns:
            typing.Any: stored cached value
        """
        return self.__resolved

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

    def as_path(self):
        return self.node.path.with_suffix("." + self.name)

    def get(self, raw=False, resolved=False) -> typing.Any:
        """Get attribute value. If no arguments were specified - will return cached value.

        Args:
            raw (bool, optional): get raw value. Defaults to False.
            resolved (bool, optional): get resolved value. Defaults to False.

        Returns:
            typing.Any: stored value.
        """

        if raw:
            return self.value
        elif resolved:
            return self.resolved_value
        else:
            return self.cached_value

    def set(self, value, resolve=True):
        """Set raw attribute value"""
        self.__value = value
        if resolve:
            self.resolve()

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
        return self.resolved_value == self.cached_value

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
        self.resolve()
        # If value resolves to attribute push that attribute resolved value to cache instead.
        value_to_cache = self.resolved_value.resolved_value if isinstance(
            self.resolved_value, Attribute) else self.resolved_value

        self.push(value_to_cache)

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
        LOGGER.debug(f"{self} | Resolving...")
        self.__resolved = None
        if self.value is None:
            return

        if isinstance(self.value, str):
            resolved = self._resolve_string(self.value)
            if isinstance(resolved, Attribute):
                if resolved.resolved_value and not resolved.cached_value:
                    resolved = resolved.resolved_value
                else:
                    resolved = resolved.cached_value

            self.__resolved = resolved
        else:
            self.__resolved = self.value
        LOGGER.debug(f"Resolved value: {self.resolved_value}")

    def _resolve_string(self, raw_str: str):
        LOGGER.debug(f"Resolving string value: {raw_str}")
        full_path = pathlib.PurePosixPath(raw_str)
        node_path = full_path.with_suffix("")
        if node_path not in self.stage.path_map:
            return raw_str

        attr_name = full_path.suffix.replace(".", "")
        if not attr_name:
            return raw_str

        # Resolve node path
        other_node = self.stage.node(node_path)

        if not other_node:
            return raw_str

        # Get attr value
        try:
            attr: "Attribute" = other_node[attr_name]
        except nyx_exceptions.NodeNoAttributeExistError:
            LOGGER.warning(f"{other_node} has no attr: {attr_name}")
            return raw_str

        return attr

    def connect(self, other_attr: "Attribute", resolve=True):
        other_attr.set(self.as_path().as_posix(), resolve=resolve)
        LOGGER.info(f"Connected {self} -> {other_attr}")
