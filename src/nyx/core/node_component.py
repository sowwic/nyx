import enum
import pathlib
import typing
from collections import OrderedDict

from PySide6 import QtCore, QtGui, QtWidgets

from .serializable import Serializable
from ..static.enums import NodeComponentSolveDirection

if typing.TYPE_CHECKING:
    from .node import Node
    from .models.components_model import NodeComponentsModel


class NodeComponent(QtGui.QStandardItem, Serializable):
    DEFAULT_NAME: str = "component"

    class Roles(enum.IntEnum):
        NAME = QtCore.Qt.ItemDataRole.DisplayRole
        TYPE_ID = QtCore.Qt.ItemDataRole.UserRole + 1
        TYPE_DISPLAY_NAME = enum.auto()
        VALUE = enum.auto()
        DEFAULT_VALUE = enum.auto()
        TAGS = enum.auto()
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

    def __rshift__(self, other: NodeComponent | pathlib.PurePosixPath | str):
        """Handle `self >> other` operator

        Args:
            other: other component or component path

        Raises:
            ValueError: Component with given path wasn't found in the stage.
        """
        other_component = self.node.stage.node_component(other)
        if not isinstance(other_component, NodeComponent):
            raise ValueError(f"Not a valid component path: {other}")

        other_component.value = self.as_path()

    def __rrshift__(self, other: pathlib.PurePosixPath | str):
        """Handle `other >> self` operator, when `other` doesn't
            support >> with this type.

        Args:
            other: other component or component path

        Raises:
            ValueError: Component with given path wasn't found in the stage.
        """
        other_component = self.node.stage.node_component(other)
        if not isinstance(other_component, NodeComponent):
            raise ValueError(
                f"Not a valid component: {other_component}, obtained from {other}"
            )

        self.value = other_component.as_path()

    def __lshift__(self, other: NodeComponent | pathlib.PurePosixPath | str):
        """Handle `self << other` operator

        Args:
            other: other component or component path

        Raises:
            ValueError: Component with given path wasn't found in the stage.
        """
        other_component = self.node.stage.node_component(other)
        if not isinstance(other_component, NodeComponent):
            raise ValueError(f"Not a valid component path: {other}")

        self.value = other_component.as_path()

    def __rlshift__(self, other: pathlib.PurePosixPath | str):
        """Handle `other << self` operator, when `other` doesn't
            support >> with this type.

        Args:
            other: other component or component path

        Raises:
            ValueError: Component with given path wasn't found in the stage.
        """
        other_component = self.node.stage.node_component(other)
        if not isinstance(other_component, NodeComponent):
            raise ValueError(
                f"Not a valid component: {other_component}, obtained from {other}"
            )

        other_component.value = self.as_path()

    def model(self) -> NodeComponentsModel:
        return super().model()

    @property
    def node(self) -> Node:
        return self.model().node

    @property
    def name(self) -> str:
        return self.data(self.Roles.NAME)

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
    def default_value(self) -> typing.Any:
        return self.data(self.Roles.DEFAULT_VALUE)

    @default_value.setter
    def default_value(self, value):
        self.setData(value, self.Roles.DEFAULT_VALUE)

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

    @property
    def tags(self) -> set[str]:
        return self.data(self.Roles.TAGS)

    def init_default_data_values(self):
        self.setData(self.get_type_id(), role=self.Roles.TYPE_ID)
        self.setData(self.get_type_display_name(), role=self.Roles.TYPE_DISPLAY_NAME)
        self.setData(self.get_tags(), role=self.Roles.TAGS)

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

    def reset_value_to_default(self) -> None:
        self.value = self.default_value

    def reset_value_to_type_default(self) -> None:
        self.value = self.get_type_default_value()

    def serialize_value(self) -> typing.Any:
        return self.value

    def deserialize_value(self, value: typing.Any) -> typing.Any:
        return value

    def serialize_default_value(self) -> typing.Any:
        return self.default_value

    def deserialize_default_value(self, value: typing.Any) -> typing.Any:
        return value

    def serialize(self) -> OrderedDict[str, typing.Any]:
        data = super().serialize()
        data["type_id"] = self.get_type_id()
        data["name"] = self.name
        data["value"] = self.serialize_value()
        data["default_value"] = self.serialize_default_value()
        data["is_active"] = self.is_active
        data["is_readable"] = self.is_readable
        data["is_writable"] = self.is_writable
        return data

    def deserialize(self, data: OrderedDict):
        self.name = data["name"]
        self.value = self.deserialize_value(value=data["value"])
        self.default_value = self.deserialize_default_value(
            value=data.get("default_value")
        )
        self.is_active = data["is_active"]
        self.is_readable = data["is_readable"]
        self.is_writable = data["is_writable"]
        return super().deserialize(data)

    def execute(self):
        if not self.is_active:
            return

    @classmethod
    def get_solve_direction(self):
        return NodeComponentSolveDirection.BACKWARD

    @classmethod
    def get_type_default_value(self) -> typing.Any:
        return None

    @classmethod
    def get_type_id(cls) -> str:
        return "base_component"

    @classmethod
    def get_type_display_name(cls) -> str:
        return cls.__name__

    @classmethod
    def get_tags(cls) -> set[str]:
        return set()
