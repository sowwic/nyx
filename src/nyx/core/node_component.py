import enum
import pathlib
import typing
import logging
from collections import OrderedDict

from PySide6 import QtCore, QtGui, QtWidgets
from uuid import UUID

from .stage_object import StageObject
from .plugin_subsystem.registry import NYX_REGISTRY
from ..static.enums import RestoreUuidOption, NodeComponentFlag

if typing.TYPE_CHECKING:
    from .node import Node
    from .stage import Stage
    from .link import Link
    from .models.components_model import NodeComponentsModel

type NodeComponentLike = NodeComponent | UUID | pathlib.PurePosixPath | str

LOGGER = logging.getLogger(__name__)


class NodeComponent(QtGui.QStandardItem, StageObject):
    DEFAULT_NAME: str = "component"
    PATH_SEPARATOR = "."

    TYPE_ID_KEY = "type_id"
    NAME_KEY = "name"
    ACTIVE_KEY = "active"
    LINKS_KEY = "links"

    class Roles(enum.IntEnum):
        NAME = QtCore.Qt.ItemDataRole.DisplayRole
        TYPE_ID_ROLE = QtCore.Qt.ItemDataRole.UserRole + 1
        TYPE_DISPLAY_NAME_ROLE = enum.auto()
        VALUE = enum.auto()
        LINKS_ROLE = enum.auto()
        DEFAULT_VALUE = enum.auto()
        TAGS_ROLE = enum.auto()
        FLAGS_ROLE = enum.auto()
        IS_ACTIVE = enum.auto()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__} ({self.path})"

    def __init__(
        self,
        name: str | None = None,
        uuid: UUID | None = None,
    ):
        QtGui.QStandardItem.__init__(self)
        StageObject.__init__(self, uuid=uuid)

        self.name = name or self.DEFAULT_NAME
        self.init_default_data_values()

    def __rshift__(self, other: NodeComponent | pathlib.PurePosixPath | str) -> Link:
        """Handle `self >> other` operator

        Args:
            other: other component or component path

        Raises:
            ValueError: Component with given path wasn't found in the stage.
        """
        other_component = self.node.stage.get_object(other)
        if not isinstance(other_component, NodeComponent):
            raise ValueError(f"Not a valid component path: {other}")

        return self.stage.link_components(
            source_component=self, target_component=other_component
        )

    def __rrshift__(self, other: pathlib.PurePosixPath | str) -> Link:
        """Handle `other >> self` operator, when `other` doesn't
            support >> with this type.

        Args:
            other: other component or component path

        Raises:
            ValueError: Component with given path wasn't found in the stage.
        """
        other_component = self.node.stage.get_object(other)
        if not isinstance(other_component, NodeComponent):
            raise ValueError(
                f"Not a valid component: {other_component}, obtained from {other}"
            )

        return self.stage.link_components(
            source_component=other_component, target_component=self
        )

    def __lshift__(self, other: NodeComponent | pathlib.PurePosixPath | str) -> Link:
        """Handle `self << other` operator

        Args:
            other: other component or component path

        Raises:
            ValueError: Component with given path wasn't found in the stage.
        """
        other_component = self.node.stage.get_object(other)
        if not isinstance(other_component, NodeComponent):
            raise ValueError(f"Not a valid component path: {other}")

        return self.stage.link_components(
            source_component=other_component, target_component=self
        )

    def __rlshift__(self, other: pathlib.PurePosixPath | str) -> Link:
        """Handle `other << self` operator, when `other` doesn't
            support >> with this type.

        Args:
            other: other component or component path

        Raises:
            ValueError: Component with given path wasn't found in the stage.
        """
        other_component = self.node.stage.get_object(other)
        if not isinstance(other_component, NodeComponent):
            raise ValueError(
                f"Not a valid component: {other_component}, obtained from {other}"
            )

        return self.stage.link_components(
            source_component=self, target_component=other_component
        )

    def model(self) -> NodeComponentsModel:
        return super().model()

    @property
    def node(self) -> Node:
        return self.model().node

    @property
    def stage(self) -> Stage:
        return self.node.stage

    @property
    def path(self) -> pathlib.PurePosixPath:
        return self.node.path.with_suffix(self.PATH_SEPARATOR + self.name)

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
    def links_uuids(self) -> frozenset[UUID]:
        return self.data(self.Roles.LINKS_ROLE)

    @property
    def output_links_uuids(self) -> list[UUID]:
        return [link.uuid for link in self.output_links]

    @property
    def input_links_uuids(self) -> list[UUID]:
        return [link.uuid for link in self.input_links]

    @property
    def links(self) -> list[Link]:
        return [self.stage.get_object(uuid) for uuid in list(self.links_uuids)]

    @property
    def output_links(self) -> list[Link]:
        return [link for link in self.links if link.source_component is self]

    @property
    def input_links(self) -> list[Link]:
        return [link for link in self.links if link.target_component is self]

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
    def produces_output(self) -> bool:
        return NodeComponentFlag.PRODUCES_OUTPUT in self.component_flags

    @produces_output.setter
    def produces_output(self, state: bool) -> None:
        if state:
            self.component_flags |= NodeComponentFlag.PRODUCES_OUTPUT
        else:
            self.component_flags &= ~NodeComponentFlag.PRODUCES_OUTPUT

    @property
    def accepts_input(self) -> bool:
        return NodeComponentFlag.ACCEPTS_INPUTS in self.component_flags

    @accepts_input.setter
    def accepts_input(self, state: bool) -> None:
        if state:
            self.component_flags |= NodeComponentFlag.ACCEPTS_INPUTS
        else:
            self.component_flags &= ~NodeComponentFlag.ACCEPTS_INPUTS

    @property
    def is_built_in(self) -> bool:
        return NodeComponentFlag.BUILT_IN in self.component_flags

    @property
    def tags(self) -> set[str]:
        return self.data(self.Roles.TAGS_ROLE)

    @property
    def component_flags(self) -> NodeComponentFlag:
        return self.data(self.Roles.FLAGS_ROLE)

    @component_flags.setter
    def component_flags(self, flags: NodeComponentFlag) -> None:
        self.setData(flags, role=self.Roles.FLAGS_ROLE)

    def init_default_data_values(self):
        self.setData(self.get_type_id(), role=self.Roles.TYPE_ID_ROLE)
        self.setData(
            self.get_type_display_name(), role=self.Roles.TYPE_DISPLAY_NAME_ROLE
        )
        self.setData(self.get_tags(), role=self.Roles.TAGS_ROLE)
        self.setData(set(), role=self.Roles.LINKS_ROLE)
        self.component_flags = self.get_type_default_flags()

        self.is_active = True
        self.produces_output = False
        self.accepts_input = False
        self.value = None

    def mark_as_built_in(self):
        self.component_flags |= NodeComponentFlag.BUILT_IN

    def create_inspector_widget(self, parent) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget(parent)
        layout = QtWidgets.QHBoxLayout()
        line_edit = QtWidgets.QLineEdit()
        widget.setLayout(layout)
        layout.addWidget(line_edit)
        return widget

    def pull_value(self) -> typing.Any:
        input_links = self.input_links
        if input_links:
            return input_links[0].source_component.value
        return self.value

    def reset_value_to_default(self) -> None:
        self.value = self.default_value

    def reset_value_to_type_default(self) -> None:
        self.value = self.get_type_default_value()

    def add_link(self, link_uuid: UUID | str):
        self.data(self.Roles.LINKS_ROLE).add(link_uuid)

    def remove_link(self, link_uuid: UUID | str):
        self.data(self.Roles.LINKS_ROLE).discard(link_uuid)

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
        data["flags"] = self.component_flags
        data["name"] = self.name
        data["value"] = self.serialize_value()
        data["default_value"] = self.serialize_default_value()
        data["is_active"] = self.is_active
        data["links"] = [link.serialize() for link in self.links]
        return data

    @classmethod
    def deserialize(
        cls,
        data: OrderedDict,
        node: Node,
        component: NodeComponent | None = None,
        restore_uuid=RestoreUuidOption.ATTEMPT_RESTORE,
    ):
        uuid = cls.choose_new_uuid(
            node.stage, serialized_data=data, restore_option=restore_uuid
        )
        if not component:
            component_cls = NYX_REGISTRY.get_node_component_cls(data[cls.TYPE_ID_KEY])
            component = component_cls(uuid=uuid)

        component.uuid = uuid
        component.name = data["name"]
        component.value = component.deserialize_value(value=data["value"])
        component.default_value = component.deserialize_default_value(
            value=data.get("default_value")
        )
        component.is_active = data["is_active"]
        component.component_flags = NodeComponentFlag(data["flags"])

        component.deserialize_links(
            links_data=data[cls.LINKS_KEY], restore_uuid=restore_uuid
        )
        return component

    def deserialize_links(
        self,
        links_data: list[OrderedDict[str, typing.Any]],
        restore_uuid: RestoreUuidOption,
    ):
        for each_link_data in links_data:
            link = Link.deserialize(
                stage=self.stage,
                serialized_link=each_link_data,
                link=None,
                restore_uuid=restore_uuid,
            )
            self.stage.register_link(link)

    def execution_hook(self):
        if not self.is_active:
            return
        self.execute()

    def evaluation_hook(self):
        if not self.is_active:
            return
        self.evaluate()

    def evaluate(self):
        pass

    def execute(self):
        pass

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
    def get_type_default_flags(cls) -> NodeComponentFlag:
        return NodeComponentFlag.NONE

    @classmethod
    def get_tags(cls) -> set[str]:
        return set()
