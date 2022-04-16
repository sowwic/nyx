from PySide2 import QtGui
from nyx.utils import inspect_fn
from nyx import get_main_logger
from collections import deque

LOGGER = get_main_logger()


class Node(QtGui.QStandardItem):

    def __repr__(self) -> str:
        return f"{inspect_fn.class_string(self.__class__)}({self.text()})"

    def __init__(self, name: str, parent=None) -> None:
        super().__init__(name)

    @property
    def stage(self):
        return self.model()

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
