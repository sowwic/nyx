import typing
import pathlib
from PySide6 import QtGui, QtWidgets

from .serializable import Serializable

if typing.TYPE_CHECKING:
    from .node import Node


class NodeComponentsModel(QtGui.QStandardItemModel, Serializable):
    def __init__(self, node):
        self._node = node
        QtGui.QStandardItemModel.__init__(self)
        Serializable.__init__(self)


class NodeComponent(QtGui.QStandardItem, Serializable):
    TYPE_ID: str = ""
    CATEGORY: pathlib.PurePosixPath | None = None
    DEFAULT_NAME: str = "Component"

    def __init__(
        self,
        node: "Node | pathlib.PurePosixPath | str",
        has_input: bool = False,
        has_output: bool = False,
    ):
        QtGui.QStandardItem.__init__(self)
        Serializable.__init__(self)
        self._node = node
        self._has_input = has_input
        self._has_output = has_output

    def create_inspector_widget(self, parent) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget(parent)
        layout = QtWidgets.QHBoxLayout()
        line_edit = QtWidgets.QLineEdit()
        widget.setLayout(layout)
        layout.addWidget(line_edit)
        return widget

    def load_from_component(self): ...

    def apply_to_component(self): ...

    def serialize(self):
        data = super().serialize()

        return data
