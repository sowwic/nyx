import enum
import pathlib
import typing
import logging
from collections import OrderedDict

from PySide6 import QtCore, QtGui
from uuid import UUID

from .stage_object import StageObject
from .link import Link
from .contexts.serialization import NodeDeserializationContext
from .plugin_subsystem.registry import NYX_REGISTRY
from ..static.enums import RestoreUuidOption, NodeComponentFlag
from ..static.paths import DEFAULT_QML_NODE_COMPONENT_ITEM

if typing.TYPE_CHECKING:
    from .node import Node
    from .stage import Stage
    from .models.components_model import NodeComponentsModel

type NodeComponentLike = NodeComponent | UUID | pathlib.PurePosixPath | str

LOGGER = logging.getLogger(__name__)


class NodeComponent(QtGui.QStandardItem, StageObject):
    DEFAULT_NAME: str = "component"
    EDITOR_QML: str | None = None
    PATH_SEPARATOR: str = "."

    TYPE_ID_KEY = "type_id"
    NAME_KEY = "name"
    ACTIVE_KEY = "active"

    class Roles(enum.IntEnum):
        NAME = QtCore.Qt.ItemDataRole.DisplayRole
        TYPE_ID = QtCore.Qt.ItemDataRole.UserRole + 1
        TYPE_DISPLAY_NAME = enum.auto()
        TYPE_ICON = enum.auto()
        VALUE = enum.auto()
        LINKS = enum.auto()
        DEFAULT_VALUE = enum.auto()
        TAGS = enum.auto()
        COMPONENT_FLAGS = enum.auto()
        IS_ACTIVE = enum.auto()
        IS_EXPANDED = enum.auto()
        # Virtual roles, computed in NodeComponentsModel.data()
        UUID = enum.auto()
        PATH = enum.auto()
        NODE = enum.auto()
        EDITOR_QML_FILE = enum.auto()
        IS_EDITABLE = enum.auto()
        IS_STATIC = enum.auto()
        IS_BUILT_IN = enum.auto()

        @classmethod
        def virtual_roles(cls):
            return (
                cls.UUID,
                cls.PATH,
                cls.NODE,
                cls.EDITOR_QML_FILE,
                cls.IS_BUILT_IN,
                cls.IS_EDITABLE,
                cls.IS_STATIC,
            )

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
        return self.data(self.Roles.LINKS)

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
    def is_editable(self) -> bool:
        return NodeComponentFlag.EDITABLE in self.component_flags

    @is_editable.setter
    def is_editable(self, state: bool) -> None:
        if state:
            self.component_flags |= NodeComponentFlag.EDITABLE
        else:
            self.component_flags &= ~NodeComponentFlag.EDITABLE

    @property
    def is_static(self) -> bool:
        return NodeComponentFlag.STATIC in self.component_flags

    @is_static.setter
    def is_static(self, state: bool) -> None:
        if state:
            self.component_flags |= NodeComponentFlag.STATIC
        else:
            self.component_flags &= ~NodeComponentFlag.STATIC

    @property
    def is_built_in(self) -> bool:
        return NodeComponentFlag.BUILT_IN in self.component_flags

    @property
    def tags(self) -> set[str]:
        return self.data(self.Roles.TAGS)

    @property
    def component_flags(self) -> NodeComponentFlag:
        return self.data(self.Roles.COMPONENT_FLAGS) or NodeComponentFlag.NONE

    @component_flags.setter
    def component_flags(self, flags: NodeComponentFlag) -> None:
        self.setData(flags, role=self.Roles.COMPONENT_FLAGS)

    @property
    def is_expanded(self) -> bool:
        return bool(self.data(self.Roles.IS_EXPANDED))

    @is_expanded.setter
    def is_expanded(self, state: bool) -> None:
        self.setData(state, role=self.Roles.IS_EXPANDED)

    def init_default_data_values(self):
        self.setData(self.get_type_id(), role=self.Roles.TYPE_ID)
        self.setData(self.get_type_display_name(), role=self.Roles.TYPE_DISPLAY_NAME)
        self.setData(self.get_type_icon(), role=self.Roles.TYPE_ICON)
        self.setData(self.get_tags(), role=self.Roles.TAGS)
        self.setData(set(), role=self.Roles.LINKS)
        self.component_flags = self.get_type_default_flags()

        self.is_active = True
        self.is_expanded = self.get_default_expanded_state()
        self.value = None

    def mark_as_built_in(self):
        self.component_flags |= NodeComponentFlag.BUILT_IN

    def pull_value(self) -> typing.Any:
        input_links = self.input_links
        if input_links:
            return input_links[0].source_component.pull_value()
        return self.value

    def reset_value_to_default(self) -> None:
        self.value = self.default_value

    def reset_value_to_type_default(self) -> None:
        self.value = self.get_type_default_value()

    def add_link(self, link_uuid: UUID | str):
        self.data(self.Roles.LINKS).add(link_uuid)

    def remove_link(self, link_uuid: UUID | str):
        self.data(self.Roles.LINKS).discard(link_uuid)

    def is_linked_to(
        self, other_component: NodeComponent, as_source=False, as_target=False
    ) -> bool:
        linked_as_source = False
        linked_as_target = False

        for link in self.links:
            if link.source == self.uuid and link.target == other_component.uuid:
                linked_as_source = True
            if link.source == other_component.uuid and link.target == self.uuid:
                linked_as_target = True
        if as_source:
            return linked_as_source
        if as_target:
            return linked_as_target
        return linked_as_source or linked_as_target

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
        return data

    @classmethod
    def deserialize(
        cls,
        data: OrderedDict,
        node: Node,
        context: NodeDeserializationContext,
        component: NodeComponent | None = None,
        restore_uuid=RestoreUuidOption.ATTEMPT_RESTORE,
    ) -> NodeComponent:
        uuid = cls.choose_new_uuid(
            node.stage, serialized_data=data, restore_option=restore_uuid
        )
        if not component:
            component_cls = NYX_REGISTRY.get_node_component_cls(data[cls.TYPE_ID_KEY])
            component = component_cls(uuid=uuid)

        component.uuid = uuid
        context.register(serialized_uuid=data.get(cls.UUID_KEY), new_uuid=component.uuid)
        component.name = data["name"]
        component.value = component.deserialize_value(value=data["value"])
        component.default_value = component.deserialize_default_value(
            value=data.get("default_value")
        )
        component.is_active = data["is_active"]
        component.component_flags = NodeComponentFlag(data["flags"])

        return component

    def execution_hook(self):
        if self.is_static:
            return
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
    def get_qml_editor_url(cls) -> QtCore.QUrl:
        if cls.EDITOR_QML and cls.SOURCE_PLUGIN:
            return cls.resolve_qml_source(cls.EDITOR_QML)
        return QtCore.QUrl.fromLocalFile(str(DEFAULT_QML_NODE_COMPONENT_ITEM))

    @classmethod
    def get_type_default_value(self) -> typing.Any:
        return None

    @classmethod
    def get_type_id(cls) -> str:
        raise NotImplementedError

    @classmethod
    def get_type_display_name(cls) -> str:
        return cls.__name__

    @classmethod
    def get_type_default_flags(cls) -> NodeComponentFlag:
        return NodeComponentFlag.NONE

    @classmethod
    def get_tags(cls) -> set[str]:
        return set()

    @classmethod
    def get_default_expanded_state(cls) -> bool:
        return False
