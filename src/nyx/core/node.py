import typing
from collections import deque
from collections import OrderedDict
from PySide2 import QtCore
from PySide2 import QtGui

from nyx.core.attribute import Attribute
from nyx.core.serializable import Serializable
from nyx.utils import inspect_fn
from nyx import get_main_logger

if typing.TYPE_CHECKING:
    from nyx.core import Stage


LOGGER = get_main_logger()


class Node(QtGui.QStandardItem, Serializable):

    ATTRIBUTES_ROLE = QtCore.Qt.UserRole + 1

    def __init__(self, name: str) -> None:
        QtGui.QStandardItem.__init__(self, name)
        Serializable.__init__(self)
        self.setData(OrderedDict(), role=Node.ATTRIBUTES_ROLE)

    def __repr__(self) -> str:
        return f"{inspect_fn.class_string(self.__class__)}({self.text()})"

    def __getitem__(self, key) -> Attribute:
        return self.attributes[key]

    def __setitem__(self, key: str, value):
        data = self.attributes
        if key not in data:
            data[key] = Attribute(self, value)
            LOGGER.debug(f"Added {data[key]}")
        else:
            data[key].set_value(value)
        self.setData(data, role=Node.ATTRIBUTES_ROLE)

    @property
    def stage(self) -> "Stage":
        return self.model()

    @property
    def attributes(self) -> "OrderedDict[str, Attribute]":
        return self.data(role=Node.ATTRIBUTES_ROLE)

    def get_parent(self) -> "Node":
        return self.parent() or self.stage.invisibleRootItem()

    def list_children(self):
        # type: () -> list[Node]
        return [self.child(row) for row in range(self.rowCount())]

    def list_parents(self, as_queue=False):
        # type: (bool) -> list[Node]
        parents = deque()
        if self.parent():
            parents.appendleft(self.parent())
            parents.extendleft(self.parent().list_parents())
        return parents if as_queue else list(parents)

    def path(self):
        # type: () -> list[Node]
        parents = self.list_parents(as_queue=True)
        parents.append(self)
        return list(parents)

    def delete(self):
        self.stage.delete_node(self)

    def get_attr(self, name: str) -> Attribute:
        return self[name]

    def set_attr(self, name: str, value):
        self[name] = value

    def delete_attr(self, name: str):
        data = self.attributes
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

        data = self.attributes
        if name not in data.keys():
            LOGGER.warning(f"Can't rename attribute {name} that doesn't exist!")
            return
        data[new_name] = data.pop(name)
        self.setData(data, role=Node.ATTRIBUTES_ROLE)

    def on_changed(self):
        pass

    def resolve(self):
        for attr in self.attributes.values():
            attr.resolve()

    def serialize(self) -> OrderedDict:
        data = super().serialize()
        data["name"] = self.text()
        children = [child.serialize() for child in self.list_children()]
        attributes = [attr.serialize() for _, attr in self.attributes.items()]
        data["attributes"] = attributes
        data["children"] = children
        return data

    # TODO: Add implementation
    def deserialize(self, data: OrderedDict, hashmap: dict = None, restore_id=True):
        super().deserialize(data, hashmap, restore_id=restore_id)
