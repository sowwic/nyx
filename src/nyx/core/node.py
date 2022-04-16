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
        return [self.child(row) for row in range(self.rowCount())]

    def list_parents(self):
        parents = deque()
        if self.parent():
            parents.appendleft(self.parent())
            parents.extendleft(self.parent().list_parents())
        return parents

    def path(self):
        parents = self.list_parents()
        parents.append(self)
        return parents
