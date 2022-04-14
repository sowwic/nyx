import pathlib
from PySide2 import QtCore


class NodeModelSignals:
    data_changed = QtCore.Signal(dict)
    name_changed = QtCore.Signal(str)
    path_changed = QtCore.Signal(pathlib.Path)


class NodeModel:
    def __init__(self, node_path=pathlib.Path) -> None:
        super().__init__()
        self.signals = NodeModelSignals()
        self.__path = node_path
        self.data = {}

    @property
    def path(self):
        return self.__path
