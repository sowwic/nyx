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
    DEFAULT_NAME: str = "component"
    TAGS: list[str] = []

    class Roles(enum.IntEnum):
        NAME = QtCore.Qt.ItemDataRole.DisplayRole
        TYPE_ID = QtCore.Qt.ItemDataRole.UserRole + 1
        VALUE = enum.auto()
        IS_BUILT_IN = enum.auto()
        IS_ACTIVE = enum.auto()
        IS_READABLE = enum.auto()
        IS_WRITABLE = enum.auto()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__} ({self.name})"

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

    @property
    def is_readable(self) -> bool:
        return self.data(self.Roles.IS_READABLE)

    @is_readable.setter
    def is_readable(self, state: bool) -> None:
        self.setData(state, self.Roles.IS_READABLE)

    @property
    def is_writable(self) -> bool:
        return self.data(self.Roles.IS_WRITABLE)

    @is_writable.setter
    def is_writable(self, state: bool) -> None:
        self.setData(state, self.Roles.IS_WRITABLE)

    @property
    def is_built_in(self) -> bool:
        return self.data(self.Roles.IS_BUILT_IN)

    def mark_as_built_in(self):
        self.setData(True, self.Roles.IS_BUILT_IN)

    def init_default_data_values(self):
        self.setData(self.TYPE_ID, self.Roles.TYPE_ID)
        self.is_active = True
        self.is_readable = False
        self.is_writable = False
        self.value = None

    def as_path(self) -> pathlib.PurePosixPath:
        return self.node.path.with_suffix("." + self.name)

    def create_inspector_widget(self, parent) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget(parent)
        layout = QtWidgets.QHBoxLayout()
        line_edit = QtWidgets.QLineEdit()
        widget.setLayout(layout)
        layout.addWidget(line_edit)
        return widget

    def serialize_value(self) -> typing.Any:
        return self.value

    def deserialize_value(self, value: typing.Any) -> typing.Any:
        return value

    def serialize(self) -> OrderedDict[str, typing.Any]:
        data = super().serialize()
        data["type_id"] = self.TYPE_ID
        data["name"] = self.name
        data["value"] = self.serialize_value()
        data["is_active"] = self.is_active
        data["is_readable"] = self.is_readable
        data["is_writable"] = self.is_writable
        return data

    def deserialize(self, data: OrderedDict):
        self.name = data["name"]
        self.value = self.deserialize_value(value=data["value"])
        self.is_active = data["is_active"]
        self.is_readable = data["is_readable"]
        self.is_writable = data["is_writable"]
        return super().deserialize(data)

    def execute(self):
        if not self.is_active:
            return
