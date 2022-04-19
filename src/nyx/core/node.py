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
            data[key].set_value(value)
        self.setData(data, role=Node.ATTRIBUTES_ROLE)

    @property
    def name(self):
        return self.text()

    @property
    def path(self):
        path = pathlib.Path()
        if not self.parent():
            return path / self.name
        return self.parent().path / self.name

    @property
    def stage(self) -> "Stage":
        return self.model()

    @property
    def attribs(self) -> "OrderedDict[str, Attribute]":
        return self.data(role=Node.ATTRIBUTES_ROLE)

    @property
    def python_code(self) -> str:
        return self.data(role=self.PYTHON_CODE_ROLE)

    def appendRow(self, items: typing.Sequence) -> None:
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

    def generate_unique_child_name(self, name):
        child_names = self.child_names_set()
        if name in child_names:
            index = 1
            while f"{name}{index}" in child_names:
                index += 1
            return name + str(index)
        return name

    def rename(self, new_name):
        if new_name == self.name:
            return

        if not self.parent():
            new_name = self.stage.generate_unique_child_name(new_name)
        else:
            new_name = self.parent().generate_unique_child_name(new_name)
        self.setText(new_name)
        self._update_pathmap_entry()

    def _update_pathmap_entry(self):
        self.stage.path_map.pop(self._cached_path)
        self.stage.path_map[self.path] = self
        self._cached_path = self.path
        for child_node in self.list_children():
            child_node._update_pathmap_entry()

    def get_parent(self) -> "Node":
        root = self.stage.invisibleRootItem() if self.stage else None
        return self.parent() or root

    def child_names_set(self):
        return {node.text() for node in self.list_children()}

    def list_children(self):
        # type: (bool) -> list[Node]
        children = [self.child(row) for row in range(self.rowCount())]
        return children

    def list_children_tree(self):
        children = self.list_children()
        for child in children:
            children += child.list_children()
        return children

    def list_parents(self, as_queue=False):
        # type: (bool) -> list[Node]
        parents = deque()
        if self.parent():
            parents.appendleft(self.parent())
            parents.extendleft(self.parent().list_parents())
        return parents if as_queue else list(parents)

    def delete(self):
        self.stage.delete_node(self)

    def get_attr(self, name: str) -> Attribute:
        return self[name]

    def set_attr(self, name: str, value):
        self[name] = value

    def delete_attr(self, name: str):
        data = self.attribs
        if name not in data.keys():
            LOGGER.warning(f"Can't delete attribute {name} that doesn't exist!")
            return
        data.pop(name)
        self.setData(data, role=Node.ATTRIBUTES_ROLE)
        LOGGER.debug(f"{self}: deleted attr {name}")

    def rename_attr(self, name: str, new_name: str):
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
        resolved_attrs = OrderedDict()
        for parent in self.list_parents(as_queue=True):
            resolved_attrs.update(parent.attribs)
        resolved_attrs.update(self.attribs)
        return resolved_attrs

    def on_changed(self):
        pass

    def serialize(self) -> OrderedDict:
        data = super().serialize()
        data["name"] = self.text()
        children = [child.serialize() for child in self.list_children()]
        attribs = [attr.serialize() for _, attr in self.attribs.items()]
        data["path"] = self.path.as_posix()
        data["attribs"] = attribs
        data["children"] = children
        data["code"] = self.python_code
        return data

    # TODO: Add implementation
    def deserialize(self, data: OrderedDict, hashmap: dict = None, restore_id=True):
        super().deserialize(data, hashmap, restore_id=restore_id)

    def export_to_json(self, file_path: pathlib.Path):
        data = self.serialize()
        file_fn.write_json(file_path, data)

    def load_from_json(self, file_path: pathlib.Path, as_reference=False):
        json_data = file_fn.load_json(file_path, object_pairs_hook=OrderedDict)
        self.deserialize(json_data, {}, restore_id=False)

    def get_python_code(self) -> str:
        return self.python_code

    def set_python_code(self, code_str) -> None:
        self.setData(code_str, role=Node.PYTHON_CODE_ROLE)

    def resolve_python_code(self) -> str:
        pass

    def resolve(self):
        for attr in self.attribs.values():
            attr.resolve()

    def execute_code(self):
        exec(self.python_code, {"self": self})
