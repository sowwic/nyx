from collections import deque
from collections import OrderedDict
from PySide2 import QtCore
from PySide2 import QtGui

from nyx.core.attribute import Attribute
from nyx.core.serializable import Serializable
from nyx.utils import inspect_fn
from nyx import get_main_logger

LOGGER = get_main_logger()


class Node(QtGui.QStandardItem, Serializable):

    ATTRIBUTES_ROLE = QtCore.Qt.UserRole + 1

    def __repr__(self) -> str:
        return f"{inspect_fn.class_string(self.__class__)}({self.text()})"

    def __getitem__(self, key) -> Attribute:
        return self.attributes[key]

    def __setitem__(self, key: str, value):
        data = self.attributes
        if key not in data:
            data[key] = Attribute(self, key, value)
        else:
            data[key].set_value(value)
        self.setData(data, role=Node.ATTRIBUTES_ROLE)

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.setData(OrderedDict(), role=Node.ATTRIBUTES_ROLE)

    @property
    def stage(self):
        return self.model()

    @property
    def attributes(self):
        return self.data(role=Node.ATTRIBUTES_ROLE)

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
