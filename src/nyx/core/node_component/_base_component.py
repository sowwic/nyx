import enum
import pathlib
import typing
from collections import OrderedDict

from PySide6 import QtCore, QtGui, QtWidgets

from ..serializable import Serializable

if typing.TYPE_CHECKING:
    from ..node import Node
    from .components_model import NodeComponentsModel



EMPTY_LINKS_DICT = {
    "inputs": [],
    "outputs": []
}


class NodeComponent(QtGui.QStandardItem, Serializable):
    TYPE_ID: str = "base_component"
    DEFAULT_NAME: str = "Component"
    CATEGORY: pathlib.PurePosixPath | None = None

    class Roles(enum.IntEnum):
        NAME = QtCore.Qt.ItemDataRole.DisplayRole
        VALUE = QtCore.Qt.ItemDataRole.UserRole + 1
        LINKS = enum.auto()
        IS_ACTIVE = enum.auto()
        IS_READABLE = enum.auto()
        IS_WRITABLE = enum.auto()

    def __init__(
        self,
        name: str | None = None,
        is_readable: bool = False,
        is_writable: bool = False,
    ):
        QtGui.QStandardItem.__init__(self)
        Serializable.__init__(self)

        self.name = name or self.DEFAULT_NAME
        self.is_writable = is_writable
        self.is_readable = is_readable
        self.init_default_data_values()

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
    def links(self) -> dict[str, list[pathlib.PurePosixPath]]:
        """Dictionary of input and output links"""
        return self.data(self.Roles.LINKS)

    @links.setter
    def links(self, new_links: dict[str, dict[str, list]]):
        inputs = new_links.get("inputs", [])
        outputs = new_links.get("outputs", [])

        input_paths = [pathlib.PurePosixPath(p) for p in inputs]
        output_paths = [pathlib.PurePosixPath(p) for p in outputs]
        converted_links = {
            "inputs": input_paths,
            "outputs": output_paths
        }
        self.setData(converted_links, self.Roles.LINKS)

    @property
    def serialized_links(self) -> dict[str, list[str]]:
        """Return serialized links as a dictionary."""
        return {k: [str(p) for p in v] for k, v in self.links.items()}

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
    def is_active(self) -> bool:
        return self.data(self.Roles.IS_ACTIVE)

    @is_active.setter
    def is_active(self, state: bool) -> None:
        self.setData(state, self.Roles.IS_ACTIVE)

    def init_default_data_values(self):
        self.links = {"inputs": [], "outputs": []}
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
        data["is_readable"] = self.is_readable
        data["is_writable"] = self.is_writable
        data["links"] = self.serialized_links
        return data

    def deserialize(self, data: OrderedDict):
        return super().deserialize(data)
