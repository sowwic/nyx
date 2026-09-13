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
    DEFAULT_NAME: str = "Component"
    CATEGORY: pathlib.PurePosixPath | None = None

    class Roles(enum.IntEnum):
        # TODO: move to enums module
        NAME = QtCore.Qt.ItemDataRole.DisplayRole
        TYPE_ID = QtCore.Qt.ItemDataRole.UserRole + 1
        VALUE = enum.auto()
        IS_ACTIVE = enum.auto()

    def __init__(
        self,
        name: str | None = None,
    ):
        QtGui.QStandardItem.__init__(self)
        Serializable.__init__(self)

        self.name = name or self.DEFAULT_NAME
        self.init_default_data_values()

    def model(self) -> NodeComponentsModel:
        return super().model()

    @property
    def node(self) -> Node:
        return self.model().node

    @property
    def name(self) -> str:
        return self.data(self.Roles.NAME)

    @property
    def type_id(self) -> str:
        return self.data(self.Roles.TYPE_ID)

    @name.setter
    def name(self, new_name: str):
        self.setData(new_name, self.Roles.NAME)

    @property
    def value(self) -> typing.Any:
        return self.data(self.Roles.VALUE)

    @value.setter
    def value(self, new_value):
        self.setData(new_value, self.Roles.VALUE)

    @property
    def is_active(self) -> bool:
        return self.data(self.Roles.IS_ACTIVE)

    @is_active.setter
    def is_active(self, state: bool) -> None:
        self.setData(state, self.Roles.IS_ACTIVE)

    def init_default_data_values(self):
        self.setData(self.TYPE_ID, self.Roles.TYPE_ID)
        self.is_active = True
        self.value = None

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
        data["value"] = self.value
        data["is_active"] = self.is_active
        return data

    def deserialize(self, data: OrderedDict):
        return super().deserialize(data)

    def evaluate(self):
        if not self.is_active:
            return
