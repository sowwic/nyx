import enum
import pathlib
import typing
import logging
from collections import OrderedDict

from PySide6 import QtCore, QtGui
from uuid import UUID

from .stage_object import StageObject
from .link import Link
from .datatypes.datatype import Datatype, value_to_class_name
from .exceptions import DatatypeCastError
from .value_storage import ValueStorage
from .contexts.serialization import NodeDeserializationContext
from .plugin_subsystem.registry import NYX_REGISTRY
from ..static.enums import (
    RestoreUuidOption,
    NodeComponentFlag,
    NodeComponentValueMask,
    GraphicsPlugShape,
    CoreDatatypes,
    NoteFormat,
)
from ..static.paths import DEFAULT_QML_NODE_COMPONENT_ITEM

if typing.TYPE_CHECKING:
    from .node import Node
    from .stage import Stage
    from .models.components_model import NodeComponentsModel

type NodeComponentLike = NodeComponent | UUID | pathlib.PurePosixPath | str

LOGGER = logging.getLogger(__name__)


class NodeComponent(QtGui.QStandardItem, StageObject):
    """Base class for components attached to a node (values, scripts, flow, ...).

    Subclasses define the component type by overriding the `get_type_*` classmethods
    and can customize evaluation and execution through the hook methods.
    """

    DEFAULT_NAME: str = "component"
    DEFAULT_PLUG_COLOR: str = "#0096FF"
    EDITOR_QML: str | None = None
    PATH_SEPARATOR: str = "."
    VALUE_STORAGE_CLS: type[ValueStorage] = ValueStorage

    GRAPHICS_OBJECT_ID = "core.plug"

    TYPE_ID_KEY = "type_id"
    NAME_KEY = "name"
    ACTIVE_KEY = "active"

    class Roles(enum.IntEnum):
        """Item data roles used to store component state in the components model."""

        NAME = QtCore.Qt.ItemDataRole.DisplayRole
        TYPE_ID = QtCore.Qt.ItemDataRole.UserRole + 1
        TYPE_DISPLAY_NAME = enum.auto()
        TYPE_ICON = enum.auto()
        DESCRIPTION = enum.auto()
        NOTE = enum.auto()
        NOTE_FORMAT = enum.auto()
        RAW_VALUE = enum.auto()
        CACHED_VALUE = enum.auto()
        DATATYPE = enum.auto()
        LINKS = enum.auto()
        DEFAULT_VALUE = enum.auto()
        TAGS = enum.auto()
        COMPONENT_FLAGS = enum.auto()
        IS_ACTIVE = enum.auto()
        IS_EXPANDED = enum.auto()
        LINKS_EXPANDED = enum.auto()
        NOTE_EXPANDED = enum.auto()
        INVALID_REASON = enum.auto()
        # Virtual roles, computed in NodeComponentsModel.data()
        UUID = enum.auto()
        PATH = enum.auto()
        NODE = enum.auto()
        INPUT_LINKS = enum.auto()
        OUTPUT_LINKS = enum.auto()
        READABLE = enum.auto()
        WRITABLE = enum.auto()
        DISPLAY_VALUE = enum.auto()
        EDITOR_QML_FILE = enum.auto()
        IS_EDITABLE = enum.auto()
        IS_STATIC = enum.auto()
        IS_BUILT_IN = enum.auto()
        IS_VALID = enum.auto()
        RESOLVED_DATATYPE = enum.auto()
        IS_DATATYPE_LOCKED = enum.auto()

        @classmethod
        def virtual_roles(cls):
            """Get roles computed on request instead of stored in item data.

            Returns:
                tuple: virtual roles.
            """
            return (
                cls.UUID,
                cls.PATH,
                cls.NODE,
                cls.INPUT_LINKS,
                cls.OUTPUT_LINKS,
                cls.DISPLAY_VALUE,
                cls.EDITOR_QML_FILE,
                cls.READABLE,
                cls.WRITABLE,
                cls.IS_BUILT_IN,
                cls.IS_EDITABLE,
                cls.IS_STATIC,
                cls.IS_VALID,
                cls.RESOLVED_DATATYPE,
                cls.IS_DATATYPE_LOCKED,
            )

    def __repr__(self) -> str:
        """str: component class and path."""
        return f"{self.__class__.__name__} ({self.path})"

    def __init__(
        self,
        name: str | None = None,
        uuid: UUID | None = None,
    ):
        """Initialize NodeComponent.

        Args:
            name (str | None): component name. Defaults to the type's default name.
            uuid (UUID | None): component uuid. Generated if omitted.
        """
        QtGui.QStandardItem.__init__(self)
        StageObject.__init__(self, uuid=uuid)

        self.value_storage = self.VALUE_STORAGE_CLS(self)
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
        """NodeComponentsModel: model holding the component."""
        return super().model()

    @property
    def node(self) -> Node:
        """Node: node owning the component."""
        return self.model().node

    @property
    def stage(self) -> Stage:
        """Stage: stage of the owning node."""
        return self.node.stage

    @property
    def path(self) -> pathlib.PurePosixPath:
        """pathlib.PurePosixPath: node path plus the component name."""
        return self.node.path.with_suffix(self.PATH_SEPARATOR + self.name)

    @property
    def name(self) -> str:
        """str: component name, unique within its node."""
        return self.data(self.Roles.NAME)

    @name.setter
    def name(self, new_name: str):
        self.setData(new_name, self.Roles.NAME)

    @property
    def raw_value(self) -> typing.Any:
        """typing.Any: value as set, before evaluation."""
        return self.value_storage.raw_value

    @property
    def cached_value(self) -> typing.Any:
        """typing.Any: evaluated value."""
        return self.value_storage.cached_value

    @property
    def display_value(self) -> str:
        """str: value text shown in the UI."""
        return self.value_storage.display_value

    @property
    def datatype_id(self) -> str:
        """str: type id of the datatype hint, kept even if it isn't registered."""
        return self.data(self.Roles.DATATYPE) or CoreDatatypes.OBJECT

    @property
    def resolved_datatype_id(self) -> str:
        """str: type id of the datatype in effect, the source's if there is one."""
        source = self.get_datatype_source()
        if source is None:
            return self.datatype_id
        return source.resolved_datatype_id

    @property
    def datatype(self) -> Datatype:
        """Datatype: datatype in effect, the object datatype if unset or unknown."""
        return NYX_REGISTRY.resolve_datatype(self.resolved_datatype_id)

    @property
    def inherits_datatype(self) -> bool:
        """bool: datatype follows the component the value comes from."""
        return NodeComponentFlag.INHERITS_DATATYPE in self.component_flags

    @property
    def is_datatype_locked(self) -> bool:
        """bool: the datatype can't be changed by the user.

        Built-ins are locked, unless they inherit their datatype and have nothing to
        inherit it from.
        """
        if self.get_datatype_source() is not None:
            return True
        node = self.node
        if node is not None and node.is_structure_locked:
            return True
        return self.is_built_in and not self.inherits_datatype

    def cast_value(self, value: typing.Any) -> typing.Any:
        """Cast an already evaluated value to the datatype of the component.

        Args:
            value (typing.Any): evaluated value.

        Raises:
            DatatypeCastError: the value can't be converted.

        Returns:
            typing.Any: converted value, the datatype default for None.
        """
        return self.value_storage.cast_value(value)

    def accepts_datatype_of(self, source: NodeComponent) -> bool:
        """Check whether the datatype of another component is compatible with this one.

        Args:
            source (NodeComponent): component providing the value.

        Returns:
            bool: this component accepts the value of the source.
        """
        return self.datatype.accepts(source.datatype)

    def get_datatype_source(self) -> NodeComponent | None:
        """Get the component the datatype is taken from, like the value is pulled.

        Returns:
            NodeComponent | None: source of the input link for components inheriting
                their datatype, None if there is none or the datatype is the own one.
        """
        if not self.inherits_datatype:
            return None
        input_links = self.input_links
        return input_links[0].source_component if input_links else None

    def set_datatype(self, type_id: str) -> None:
        """Set the datatype hint and re-evaluate the value against it.

        Args:
            type_id (str): datatype type id.
        """
        self.setData(str(type_id), role=self.Roles.DATATYPE)
        self._notify_datatype_changed()
        if self.raw_value is None:
            self.push_value(self.datatype.create_default())
            return
        self.value_storage.evaluate()
        self.value_storage.refresh_display_value()

    def _notify_datatype_changed(self):
        """Tell the model the datatype in effect changed, so views refresh."""
        model = self.model()
        if model is None:
            return
        model.dataChanged.emit(
            self.index(),
            self.index(),
            [self.Roles.RESOLVED_DATATYPE, self.Roles.IS_DATATYPE_LOCKED],
        )

    @property
    def links_uuids(self) -> frozenset[UUID]:
        """frozenset[UUID]: uuids of links connected to the component."""
        return self.data(self.Roles.LINKS)

    @property
    def output_links_uuids(self) -> list[UUID]:
        """list[UUID]: uuids of links this component is the source of."""
        return [link.uuid for link in self.output_links]

    @property
    def input_links_uuids(self) -> list[UUID]:
        """list[UUID]: uuids of links this component is the target of."""
        return [link.uuid for link in self.input_links]

    @property
    def links(self) -> list[Link]:
        """list[Link]: links connected to the component."""
        return [self.stage.get_object(uuid) for uuid in list(self.links_uuids)]

    @property
    def output_links(self) -> list[Link]:
        """list[Link]: links this component is the source of."""
        return [link for link in self.links if link.source_component is self]

    @property
    def input_links(self) -> list[Link]:
        """list[Link]: links this component is the target of."""
        return [link for link in self.links if link.target_component is self]

    @property
    def default_value(self) -> typing.Any:
        """typing.Any: value the component resets to."""
        return self.data(self.Roles.DEFAULT_VALUE)

    @default_value.setter
    def default_value(self, value):
        self.setData(value, self.Roles.DEFAULT_VALUE)

    @property
    def is_active(self) -> bool:
        """bool: component takes part in evaluation and execution."""
        return self.data(self.Roles.IS_ACTIVE)

    @is_active.setter
    def is_active(self, state: bool) -> None:
        self.setData(state, self.Roles.IS_ACTIVE)

    @property
    def readable(self) -> bool:
        """bool: component can be the source of a link."""
        return NodeComponentFlag.READABLE in self.component_flags

    @readable.setter
    def readable(self, state: bool) -> None:
        self.set_component_flag(
            NodeComponentFlag.READABLE, self.Roles.READABLE, state=state
        )

    @property
    def writable(self) -> bool:
        """bool: component can be the target of a link."""
        return NodeComponentFlag.WRITABLE in self.component_flags

    @writable.setter
    def writable(self, state: bool) -> None:
        self.set_component_flag(
            NodeComponentFlag.WRITABLE, self.Roles.WRITABLE, state=state
        )

    @property
    def single_output(self) -> bool:
        """bool: component can be the source of one link at most."""
        return NodeComponentFlag.SINGLE_OUTPUT in self.component_flags

    @property
    def is_editable(self) -> bool:
        """bool: value can be edited in the UI."""
        return NodeComponentFlag.EDITABLE in self.component_flags

    @is_editable.setter
    def is_editable(self, state: bool) -> None:
        self.set_component_flag(
            flag=NodeComponentFlag.EDITABLE, role=self.Roles.IS_EDITABLE, state=state
        )

    @property
    def is_static(self) -> bool:
        """bool: component is skipped during execution."""
        return NodeComponentFlag.STATIC in self.component_flags

    @is_static.setter
    def is_static(self, state: bool) -> None:
        self.set_component_flag(
            flag=NodeComponentFlag.STATIC, role=self.Roles.IS_STATIC, state=state
        )

    @property
    def is_valid(self) -> bool:
        """bool: the value is usable. Components with something to resolve override."""
        return self.value_storage.is_valid

    @property
    def invalid_reason(self) -> str:
        """str: why the component can't be relied on, empty if it can.

        Set by the node owning the component, like a reference node for a component
        that is not in its source anymore. Not serialized.
        """
        return self.data(self.Roles.INVALID_REASON) or ""

    @invalid_reason.setter
    def invalid_reason(self, reason: str) -> None:
        self.setData(reason, role=self.Roles.INVALID_REASON)

    @property
    def is_built_in(self) -> bool:
        """bool: component was created by the node type and can't be removed."""
        return NodeComponentFlag.BUILT_IN in self.component_flags

    @property
    def tags(self) -> set[str]:
        """set[str]: component tags."""
        return self.data(self.Roles.TAGS)

    @property
    def component_flags(self) -> NodeComponentFlag:
        """NodeComponentFlag: flags describing component behaviour."""
        return self.data(self.Roles.COMPONENT_FLAGS) or NodeComponentFlag.NONE

    @component_flags.setter
    def component_flags(self, flags: NodeComponentFlag) -> None:
        self.setData(flags, role=self.Roles.COMPONENT_FLAGS)

    @property
    def is_expanded(self) -> bool:
        """bool: component is expanded in the UI."""
        return bool(self.data(self.Roles.IS_EXPANDED))

    @is_expanded.setter
    def is_expanded(self, state: bool) -> None:
        self.setData(state, role=self.Roles.IS_EXPANDED)

    @property
    def description(self) -> str:
        """str: what the component is for, shown as its tooltip. The type description
        by default, or the type display name if the type has none."""
        return self.data(self.Roles.DESCRIPTION) or ""

    @description.setter
    def description(self, text: str) -> None:
        self.setData(text, role=self.Roles.DESCRIPTION)

    @property
    def note(self) -> str:
        """str: note the user attached to the component, empty for none."""
        return self.data(self.Roles.NOTE) or ""

    @note.setter
    def note(self, text: str) -> None:
        self.setData(text, role=self.Roles.NOTE)

    @property
    def note_format(self) -> NoteFormat:
        """NoteFormat: how the note is written."""
        return NoteFormat(self.data(self.Roles.NOTE_FORMAT) or NoteFormat.PLAIN)

    @note_format.setter
    def note_format(self, note_format: NoteFormat | str) -> None:
        self.setData(str(NoteFormat(note_format)), role=self.Roles.NOTE_FORMAT)

    @property
    def is_note_expanded(self) -> bool:
        """bool: the note frame is open in the UI."""
        return bool(self.data(self.Roles.NOTE_EXPANDED))

    @is_note_expanded.setter
    def is_note_expanded(self, state: bool) -> None:
        self.setData(state, role=self.Roles.NOTE_EXPANDED)

    def init_default_data_values(self):
        """Initialize item data roles with the defaults of the component type."""
        self.setData(self.get_type_id(), role=self.Roles.TYPE_ID)
        self.setData(self.get_type_display_name(), role=self.Roles.TYPE_DISPLAY_NAME)
        self.setData(self.get_type_icon(), role=self.Roles.TYPE_ICON)
        self.setData(
            self.get_description() or self.get_type_display_name(),
            role=self.Roles.DESCRIPTION,
        )
        self.setData("", role=self.Roles.NOTE)
        self.setData("", role=self.Roles.INVALID_REASON)
        self.setData(str(NoteFormat.PLAIN), role=self.Roles.NOTE_FORMAT)
        self.setData(str(self.get_type_default_datatype()), role=self.Roles.DATATYPE)
        self.setData(self.get_tags(), role=self.Roles.TAGS)
        self.setData(False, role=self.Roles.LINKS_EXPANDED)
        self.setData(True, role=self.Roles.NOTE_EXPANDED)
        self.setData(set(), role=self.Roles.LINKS)
        self.component_flags = self.get_type_default_flags()

        self.is_active = True
        self.is_expanded = self.get_default_expanded_state()
        self.push_value(self.get_initial_value())

    def set_component_flag(
        self, flag: NodeComponentFlag, role: NodeComponent.Roles, state: bool
    ):
        """Set or clear a component flag and notify the model.

        Args:
            flag (NodeComponentFlag): flag to change.
            role (NodeComponent.Roles): role reported as changed.
            state (bool): whether the flag is set.
        """
        if state:
            self.component_flags |= flag
        else:
            self.component_flags &= ~flag
        if self.model() is not None:
            self.model().dataChanged.emit(self.index(), self.index(), [role])

    def mark_as_built_in(self):
        """Flag the component as built-in."""
        self.component_flags |= NodeComponentFlag.BUILT_IN

    def get_display_value(self) -> str:
        """Get the display value, following the input link if there is one.

        Returns:
            str: display value, the one of the component itself if the linked value
                can't be pulled, like when the source points at something missing.
        """
        if self.input_links:
            source = self.input_links[0].source_component
            try:
                source_value = source.pull_value()
            except Exception as err:
                LOGGER.debug("%s: can't show the linked value: %s", self.path, err)
                return self.data(role=self.Roles.DISPLAY_VALUE)
            value = self._cast_linked_value(source_value)
            if type(value) is type(source_value) and value == source_value:
                return source.get_display_value()
            return str(value)
        return self.data(role=self.Roles.DISPLAY_VALUE)

    def clear_cached_value(self):
        """Clear the cached value and reset the display value to the raw value."""
        self.value_storage.clear_cache()

    def push_value(self, value: typing.Any, evaluate: bool = True):
        """Set the value of the component.

        Args:
            value (typing.Any): new raw value.
            evaluate (bool): evaluate the value after setting it.
        """
        self.value_storage.push(value, evaluate=evaluate)

    def _cast_linked_value(self, value: typing.Any) -> typing.Any:
        """Convert a value that came through an input link to the component datatype.

        Args:
            value (typing.Any): value of the source component.

        Returns:
            typing.Any: the converted value, the value as it is if it can't be converted.
        """
        try:
            return self.value_storage.cast_value(value)
        except DatatypeCastError as err:
            LOGGER.warning("%s: %s", self.path, err)
            return value

    def pull_value(
        self, value_mask: NodeComponentValueMask = NodeComponentValueMask.CACHE
    ) -> typing.Any:
        """Get the value, following the input link if there is one.

        Args:
            value_mask (NodeComponentValueMask): which value to get.

        Returns:
            typing.Any: requested value.
        """
        input_links = self.input_links
        if input_links:
            value = input_links[0].source_component.pull_value(value_mask=value_mask)
            if value_mask is NodeComponentValueMask.CACHE:
                return self._cast_linked_value(value)
            return value

        return self.value_storage.pull(value_mask)

    def evaluate_value(self) -> typing.Any:
        """Evaluate the raw value. Strings are evaluated as python expressions.

        Returns:
            typing.Any: evaluated value, the raw value if evaluation fails.
        """
        return self.value_storage.compute_value()

    def _evaluate_value(self):
        """Evaluate the raw value and store the result as the cached value."""
        self.value_storage.set_cached_value(self.evaluate_value())

    def reset_value_to_default(self) -> None:
        """Set the value to the component's default value."""
        self.push_value(self.default_value)

    def reset_value_to_type_default(self) -> None:
        """Set the value to the default value of the component type."""
        self.push_value(self.get_initial_value())

    def get_initial_value(self) -> typing.Any:
        """Get the value a new component starts with.

        Returns:
            typing.Any: the default value of the component type, or the default of
                the datatype if the type has none or its one can't be cast to it.
        """
        value = self.get_type_default_value()
        datatype = self.datatype
        if value is None:
            return datatype.create_default()
        try:
            datatype.cast(value)
        except DatatypeCastError as err:
            LOGGER.warning(
                "Default value of %s is not valid for datatype %s, using the "
                "default of the datatype: %s",
                self.get_type_id(),
                datatype.display_name,
                err,
            )
            return datatype.create_default()
        return value

    def add_link(self, link_uuid: UUID | str):
        """Register a link as connected to this component.

        Args:
            link_uuid (UUID | str): link uuid.
        """
        self.data(self.Roles.LINKS).add(link_uuid)
        self._notify_links_changed()

    def remove_link(self, link_uuid: UUID | str):
        """Unregister a link from this component.

        Args:
            link_uuid (UUID | str): link uuid.
        """
        self.data(self.Roles.LINKS).discard(link_uuid)
        self._notify_links_changed()

    def _notify_links_changed(self):
        """Tell the model the links changed, so views showing them refresh."""
        model = self.model()
        if model is None:
            return
        model.dataChanged.emit(
            self.index(),
            self.index(),
            [
                self.Roles.LINKS,
                self.Roles.INPUT_LINKS,
                self.Roles.OUTPUT_LINKS,
                self.Roles.DISPLAY_VALUE,
                self.Roles.RESOLVED_DATATYPE,
                self.Roles.IS_DATATYPE_LOCKED,
            ],
        )

    def is_linked_to(
        self, other_component: NodeComponent, as_source=False, as_target=False
    ) -> bool:
        """Check whether this component is linked to another one.

        Args:
            other_component (NodeComponent): component to check.
            as_source (bool): only count links where this component is the source.
            as_target (bool): only count links where this component is the target.

        Returns:
            bool: components are linked.
        """
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

    def restore_value(
        self, serialized_value: typing.Any, context: NodeDeserializationContext | None
    ) -> None:
        """Set the value from serialized data while deserializing.

        Components whose value refers to other stage objects override this to remap
        the object paths through the context.

        Args:
            serialized_value (typing.Any): value as written by `serialize_value`.
            context (NodeDeserializationContext | None): deserialization context.
        """
        self.push_value(self.deserialize_value(value=serialized_value))

    def serialize_value(self) -> typing.Any:
        """typing.Any: value to store when serializing, classes as their name."""
        return value_to_class_name(self.raw_value)

    def deserialize_value(self, value: typing.Any) -> typing.Any:
        """Convert a serialized value back to a value.

        Args:
            value (typing.Any): serialized value.

        Returns:
            typing.Any: restored value.
        """
        return value

    def serialize_default_value(self) -> typing.Any:
        """typing.Any: default value to store when serializing, classes as their name."""
        return value_to_class_name(self.default_value)

    def deserialize_default_value(self, value: typing.Any) -> typing.Any:
        """Convert a serialized default value back to a value.

        Args:
            value (typing.Any): serialized default value.

        Returns:
            typing.Any: restored default value.
        """
        return value

    def serialize(self) -> OrderedDict[str, typing.Any]:
        """Serialize the component.

        Returns:
            OrderedDict[str, typing.Any]: serialized data.
        """
        data = super().serialize()
        data["type_id"] = self.get_type_id()
        data["flags"] = self.component_flags
        data["name"] = self.name
        data["datatype"] = self.datatype_id
        data["value"] = self.serialize_value()
        data["default_value"] = self.serialize_default_value()
        data["is_active"] = self.is_active
        data["note"] = {"text": self.note, "format": str(self.note_format)}
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
        """Create or update a component from serialized data.

        Args:
            data (OrderedDict): serialized component.
            node (Node): node owning the component.
            context (NodeDeserializationContext): deserialization context.
            component (NodeComponent | None): existing component to update.
            restore_uuid: how the serialized uuid is restored.

        Returns:
            NodeComponent: deserialized component.
        """
        uuid = cls.choose_new_uuid(
            node.stage, serialized_data=data, restore_option=restore_uuid
        )
        if not component:
            component_cls = NYX_REGISTRY.get_node_component_cls(data[cls.TYPE_ID_KEY])
            component = component_cls(uuid=uuid)

        component.uuid = uuid
        component.restore_graphics_object_id(data)
        context.register(serialized_uuid=data.get(cls.UUID_KEY), new_uuid=component.uuid)
        component.name = data["name"]
        component.setData(
            data.get("datatype") or component.datatype_id, role=cls.Roles.DATATYPE
        )
        component.restore_value(data["value"], context)
        component.default_value = component.deserialize_default_value(
            value=data.get("default_value")
        )
        component.is_active = data["is_active"]
        note = data.get("note") or {}
        component.note = note.get("text", "")
        component.note_format = note.get("format", NoteFormat.PLAIN)
        component.component_flags = (
            NodeComponentFlag(data["flags"]) | component.get_type_enforced_flags()
        )

        return component

    def execution_hook(self):
        """Execute the component unless it is static or inactive."""
        if self.is_static:
            return
        if not self.is_active:
            return
        self.execute()

    def evaluation_hook(self):
        """Re-evaluate the component unless it is inactive."""
        self.clear_cached_value()
        if not self.is_active:
            return
        self._evaluate_value()
        self.evaluate()

    def evaluate(self):
        """Called while evaluating. Override in subclasses."""
        pass

    def execute(self):
        """Called while executing. Override in subclasses."""
        pass

    def get_plug_color(self) -> QtGui.QColor:
        """Get the color the plug of the component is drawn with.

        Returns:
            QtGui.QColor: plug color.
        """
        return QtGui.QColor(self.datatype.color)

    def get_plug_shape(self) -> GraphicsPlugShape:
        """Get the shape the plug of the component is drawn with.

        Returns:
            GraphicsPlugShape: plug shape of the datatype.
        """
        return self.datatype.plug_shape

    @classmethod
    def get_link_width_multiplier(cls) -> float:
        """Get how thick links coming out of the component are drawn.

        Returns:
            float: factor applied to the base width of a link, 1.0 is the base width.
        """
        return 1.0

    @classmethod
    def get_qml_editor_url(cls) -> QtCore.QUrl:
        """Get the QML file used to edit the component.

        Returns:
            QtCore.QUrl: editor file url, the default item if the type has none.
        """
        if cls.EDITOR_QML and cls.SOURCE_PLUGIN:
            return QtCore.QUrl.fromLocalFile(
                NYX_REGISTRY.resolve_qml_source(
                    cls.SOURCE_PLUGIN.plugin_cls.QML_MODULE_NAME, cls.EDITOR_QML
                )
            )
        return QtCore.QUrl.fromLocalFile(str(DEFAULT_QML_NODE_COMPONENT_ITEM))

    @classmethod
    def get_type_default_value(self) -> typing.Any:
        """typing.Any: initial value of the component type."""
        return None

    @classmethod
    def get_type_default_datatype(cls) -> str:
        """str: type id of the datatype new components of the type are hinted with."""
        return CoreDatatypes.OBJECT

    @classmethod
    def get_type_id(cls) -> str:
        """str: unique type id. Subclasses must implement."""
        raise NotImplementedError

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return cls.__name__

    @classmethod
    def get_type_default_flags(cls) -> NodeComponentFlag:
        """NodeComponentFlag: flags set on new components of the type."""
        return NodeComponentFlag.NONE

    @classmethod
    def get_type_enforced_flags(cls) -> NodeComponentFlag:
        """NodeComponentFlag: flags every component of the type has.

        Unlike the default flags these are also added when a component is
        deserialized, so files saved before a rule existed follow it too.
        """
        return NodeComponentFlag.NONE

    @classmethod
    def get_tags(cls) -> set[str]:
        """set[str]: tags of the component type."""
        return set()

    @classmethod
    def get_default_expanded_state(cls) -> bool:
        """bool: whether new components start expanded."""
        return False
