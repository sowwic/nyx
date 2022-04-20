import typing
import pathlib
from collections import deque
from collections import OrderedDict
from PySide2 import QtCore
from PySide2 import QtGui

from nyx.core.attribute import Attribute
from nyx.core.serializable import Serializable
from nyx.utils import inspect_fn
from nyx.utils import file_fn
from nyx import get_main_logger

if typing.TYPE_CHECKING:
    from nyx.core import Stage


LOGGER = get_main_logger()


class Node(QtGui.QStandardItem, Serializable):

    ATTRIBUTES_ROLE = QtCore.Qt.UserRole + 1
    PYTHON_CODE_ROLE = QtCore.Qt.UserRole + 2

    def __init__(self, name: str = "node", parent: "Node" = None) -> None:
        QtGui.QStandardItem.__init__(self, name)
        Serializable.__init__(self)
        self.setData(OrderedDict(), role=Node.ATTRIBUTES_ROLE)
        self.setData(str(), role=Node.PYTHON_CODE_ROLE)

        self._cached_path = None
        if parent:
            parent.appendRow(self)

    def __repr__(self) -> str:
        return f"{inspect_fn.class_string(self.__class__)}({self.text()})"

    def __getitem__(self, key) -> Attribute:
        return self.attribs[key]

    def __setitem__(self, key: str, value):
        data = self.attribs
        if key not in data:
            data[key] = Attribute(self, value)
            LOGGER.debug(f"Added {data[key]}")
        else:
            data[key].set(value)
        self.setData(data, role=Node.ATTRIBUTES_ROLE)

    @property
    def name(self):
        """Node name

        Returns:
            str: name.
        """
        return self.text()

    @property
    def scope(self):
        return tuple(self.path.parents)[0]

    @property
    def path(self) -> pathlib.PurePosixPath:
        """Get current node path.

        Returns:
            pathlib.PurePosixPath: absolute node path.
        """
        path = pathlib.PurePosixPath()
        if not self.parent():
            return path / self.name
        return self.parent().path / self.name

    @property
    def stage(self) -> "Stage":
        """Utility method pointing to node's stage (model).

        Returns:
            Stage: stage node belongs to.
        """
        return self.model()

    @property
    def attribs(self) -> "OrderedDict[str, Attribute]":
        """Node attributes dictionnary.

        Returns:
            OrderedDict[str, Attribute]: Node attributes.
        """
        return self.data(role=Node.ATTRIBUTES_ROLE)

    @property
    def python_code(self) -> str:
        """Node python code.

        Returns:
            str: python code string.
        """
        return self.data(role=self.PYTHON_CODE_ROLE)

    def appendRow(self, items: typing.Sequence) -> None:
        """Override Qt method.

        - Generates new unique name.
        - Set cached path to current.
        - Store path into stage path map.

        Args:
            items (typing.Sequence): items to append.

        Raises:
            ValueError: path exists in stage path map.
        """
        if not isinstance(items, typing.Sequence):
            items = [items]

        for node in items:
            node.setText(self.generate_unique_child_name(node.name))
            super().appendRow(node)
            if node.path in self.stage.path_map:
                LOGGER.error(f"Duplicate path: {node.path}")
                raise ValueError

            node._cached_path = node.path
            self.stage.path_map[node.path] = node

    def generate_unique_child_name(self, name: str):
        """Iterate through node children to generate unique name from given one.

        Args:
            name (str): desired name.

        Returns:
            str: unique child name.
        """
        child_names = self.child_names_set()
        if name in child_names:
            index = 1
            while f"{name}{index}" in child_names:
                index += 1
            return name + str(index)
        return name

    def rename(self, new_name):
        """Rename node.

        - Also update path for self and children in path map.

        Args:
            new_name (str): new node name.
        """
        if new_name == self.name:
            return

        if not self.parent():
            new_name = self.stage.generate_unique_child_name(new_name)
        else:
            new_name = self.parent().generate_unique_child_name(new_name)
        self.setText(new_name)
        self._update_pathmap_entry()

    def _update_pathmap_entry(self):
        """Update path stored for in stage path map."""
        self.stage.path_map.pop(self._cached_path)
        self.stage.path_map[self.path] = self
        self._cached_path = self.path
        for child_node in self.list_children():
            child_node._update_pathmap_entry()

    def child_names_set(self):
        """Get set of existing child names.

        Returns:
            set[str]: child names.
        """
        return {node.text() for node in self.list_children()}

    def list_children(self) -> "list[Node]":
        """List child nodes.

        Returns:
            list[Node]: child nodes.
        """
        children = [self.child(row) for row in range(self.rowCount())]
        return children

    def list_children_tree(self) -> "list[Node]":
        """List children tree recursively.

        Returns:
            list[Node]: child nodes tree.
        """
        children = self.list_children()
        for child in children:
            children += child.list_children()
        return children

    def list_parents(self, as_queue=False) -> "list[Node] | deque[Node]":
        """List parents recursively.

        Args:
            as_queue (bool, optional): if result should be returned as deque. Defaults to False.

        Returns:
            list[Node] | deque[Node]: parent nodes collection.
        """
        parents = deque()
        if self.parent():
            parents.appendleft(self.parent())
            parents.extendleft(self.parent().list_parents())
        return parents if as_queue else list(parents)

    def delete(self):
        """Delete this node from stage."""
        self.stage.delete_node(self)

    def get_attr(self, name: str) -> Attribute:
        """Get attribute with name.

        Args:
            name (str): attribute name.

        Returns:
            Attribute: attribute instance.
        """
        return self[name]

    def set_attr(self, name: str, value: typing.Any):
        """Set raw attribute value.

        Args:
            name (str): attribute name.
            value (typing.Any): new value.
        """
        self[name] = value

    def delete_attr(self, name: str):
        """Delete attribute.

        Args:
            name (str): attribute name.
        """
        data = self.attribs
        if name not in data.keys():
            LOGGER.warning(f"Can't delete attribute {name} that doesn't exist!")
            return
        data.pop(name)
        self.setData(data, role=Node.ATTRIBUTES_ROLE)
        LOGGER.debug(f"{self}: deleted attr {name}")

    def rename_attr(self, name: str, new_name: str):
        """Rename attribute.

        Args:
            name (str): attribute name.
            new_name (str): new attribute name.
        """
        if not new_name:
            LOGGER.error("New attribute name can't be empty string!")
            return

        data = self.attribs
        if name not in data.keys():
            LOGGER.warning(f"Can't rename attribute {name} that doesn't exist!")
            return
        data[new_name] = data.pop(name)
        self.setData(data, role=Node.ATTRIBUTES_ROLE)

    def resolved_attribs(self):
        """Dictionary of merged dicitonaries.

        parent: {a: 5, b: 10}, child: {a: 15} -> result: {a: 15, b: 10}

        Returns:
            OrderedDict: merged dictionary.
        """
        resolved_attrs = OrderedDict()
        for parent in self.list_parents(as_queue=True):
            resolved_attrs.update(parent.attribs)
        resolved_attrs.update(self.attribs)
        return resolved_attrs

    def get_node_from_relative_path(self, relative_path: pathlib.PurePosixPath) -> pathlib.PurePosixPath:
        """Get node from relative path.

        Args:
            relative_path (pathlib.PurePosixPath): relative path.

        Returns:
            pathlib.PurePosixPath: found node
        """
        return self.stage.get_node_from_relative_path(self, relative_path)

    def get_relative_path_to(self, other_node: "Node") -> pathlib.PurePosixPath:
        """Get relative path this to other node.

        Args:
            other_node (Node): other node.

        Returns:
            pathlib.PurePosixPath: relative path
        """
        return self.stage.get_relative_path_to(self, other_node)

    def get_relative_path_from(self, other_node: "Node"):
        """Get relative path from other to this node.

        Args:
            other_node (Node): other node

        Returns:
            pathlib.PurePosixPath: relative path
        """
        return self.stage.get_relative_path_to(other_node, self)

    def on_changed(self):
        pass

    def serialize(self) -> OrderedDict:
        """Serialize node to dict.

        Returns:
            OrderedDict: serialized data
        """
        data = super().serialize()
        data["name"] = self.text()
        children = [child.serialize() for child in self.list_children()]
        attribs = [attr.serialize() for _, attr in self.attribs.items()]
        data["path"] = self.path.as_posix()
        data["attribs"] = attribs
        data["children"] = children
        data["code"] = self.python_code
        return data

    def deserialize(self, data: OrderedDict, hashmap: dict, restore_id=True):
        super().deserialize(data, hashmap, restore_id=restore_id)
        if not hashmap:
            hashmap = {}

        self.setText(data.get("name", self.name))
        self.set_python_code(data.get("code", ""))
        hashmap[self.uuid] = self
        self._update_pathmap_entry()

        # Attributes
        for attr_data in data.get("attribs", {}):
            attr_name = attr_data["name"]
            self.set_attr(attr_name, attr_data.get("value"))
            self[attr_name].deserialize(attr_data, hashmap, restore_id=True)

        # Children
        for child_data in data.get("children", {}):
            child_node = Node(parent=self)
            child_node.deserialize(child_data, hashmap, restore_id=True)

    def export_to_json(self, file_path: pathlib.Path):
        """Export node to json file.

        Args:
            file_path (pathlib.Path): json file path.
        """
        data = self.serialize()
        file_fn.write_json(file_path, data)

    def load_from_json(self, file_path: pathlib.Path, as_reference=False):
        """Load node from json file.

        Args:
            file_path (pathlib.Path): json file path.
            as_reference (bool, optional): if node should be locked. Defaults to False.
        """
        json_data = file_fn.load_json(file_path, object_pairs_hook=OrderedDict)
        self.deserialize(json_data, {}, restore_id=False)

    def get_python_code(self) -> str:
        """Node python code.

        Returns:
            str: python code.
        """
        return self.python_code

    def set_python_code(self, code_str) -> None:
        """Set python code string.

        Args:
            code_str (str): python code.
        """
        self.setData(code_str, role=Node.PYTHON_CODE_ROLE)

    def resolve_python_code(self) -> str:
        pass

    def resolve(self):
        for attr in self.attribs.values():
            attr.resolve()

    def execute_code(self):
        """Execute code string."""
        exec(self.python_code, {"self": self})

    def clear_attributes_caches(self):
        """Clear all attributes caches."""
        for attr in self.attribs.values():
            attr.clear_cache()

    def cache_attributes_values(self):
        """Push current attributes values to cache."""
        for attr in self.attribs.values():
            attr.cache_current_value()
