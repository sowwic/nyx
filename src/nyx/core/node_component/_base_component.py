import enum
import pathlib
import typing
from collections import OrderedDict

from PySide6 import QtCore, QtGui, QtWidgets

from ..serializable import Serializable

if typing.TYPE_CHECKING:
    from ..node import Node
    from .components_model import NodeComponentsModel


class NodeComponent(QtGui.QStandardItem, Serializable):
    TYPE_ID: str = "base_component"
    NAMESPACE: str = "core"
    CATEGORY: pathlib.PurePosixPath | None = None
    DEFAULT_NAME: str = "Component"

    class Roles(enum.Enum):
        NAME = QtCore.Qt.ItemDataRole.DisplayRole
        IS_ACTIVE = QtCore.Qt.UserRole + 1

    def __init__(
        self,
        name: str | None = None,
        is_readable: bool = False,
        is_writable: bool = False,
    ):
        QtGui.QStandardItem.__init__(self)
        Serializable.__init__(self)
        # TODO: generate unique name
        self._name = name if name else self.DEFAULT_NAME
        self._is_readable = is_readable
        self._is_writable = is_writable

    def model(self) -> NodeComponentsModel:
        return super().model()

    @property
    def node(self) -> Node:
        return self.model().node

    @property
    def name(self) -> str:
        # TODO return name role
        return self._name

    @name.setter
    def name(self, new_name: str):
        self.setData(self.model().get_unique_component_name(new_name), self.Roles.NAME)

    @property
    def is_readable(self) -> bool:
        return self._is_readable

    @property
    def is_writable(self) -> bool:
        return self._is_writable

    @property
    def is_active(self):
        return self.data(self.Roles.IS_ACTIVE)

    def as_path(self):
        return self.node.path.with_suffix("." + self.name)

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
        data["type_id"] = self.TYPE_ID
        data["name"] = self.name
        return data

    def deserialize(self, data: OrderedDict):
        return super().deserialize(data)
