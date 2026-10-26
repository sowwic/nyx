import collections.abc
import dataclasses
import enum
import logging
import pathlib
import time
import typing
from collections import OrderedDict, deque
from collections.abc import Iterable

from uuid import UUID
from PySide6 import QtCore, QtGui

from .stage_object import StageObject
from .link import Link
from .models.components_model import NodeComponentsModel
from .contexts.serialization import NodeSerializationContext, NodeDeserializationContext
from .plugin_subsystem.registry import NYX_REGISTRY
from ..utils import file_fn, inspect_fn
from .node_render_options import NodeRenderOptions
from ..static.enums import (
    CoreGraphicsObjects,
    CoreNodes,
    RestoreUuidOption,
    NodeExecutionStatus,
    NodeExecutionOrderFlag,
    NodeFlag,
)

if typing.TYPE_CHECKING:
    from .stage import Stage
    from .node_component import NodeComponent
    from .util_object import UtilObject
    from .stage_crawler import NodeVisitor
    from nyx.stdlib.nodes.flow_start import FlowStartNode
    from nyx.stdlib.node_components.flow import FlowComponent


LOGGER = logging.getLogger(__name__)

type NodeLike = Node | UUID | pathlib.PurePosixPath | str


@dataclasses.dataclass(frozen=True)
class _SubtitleBinding:
    """Ties the subtitle of a node to one of its components.

    Attributes:
        component_name: name of the component to follow
        formatter: turns the component into the text, its display value if omitted
    """

    component_name: str
    formatter: collections.abc.Callable[[NodeComponent], str] | None = None

    def text(self, node: Node) -> str:
        """Work out the subtitle.

        Args:
            node (Node): node owning the component.

        Returns:
            str: text, empty if the node has no such component.
        """
        try:
            component = node.components_model.get_component(self.component_name)
        except ValueError:
            return ""
        try:
            text = (
                self.formatter(component)
                if self.formatter is not None
                else component.display_value
            )
        except Exception as err:
            # A subtitle is for show, a broken link must not stop the node from drawing
            LOGGER.debug("%s: can't work out the subtitle: %s", node.path, err)
            return ""
        return "" if text is None else str(text)


class Node(QtGui.QStandardItem, StageObject):
    """Stage node holding a list of components and child nodes.

    Subclasses define the node type by overriding the `get_type_*` classmethods and
    can customize setup and execution through the hook methods.
    """

    DEFAULT_NAME = "node"
    TRACK_NYX_VERSION: bool = True

    GRAPHICS_OBJECT_ID = CoreGraphicsObjects.NODE

    TYPE_ID_KEY = "type_id"
    NAME_KEY = "name"
    ACTIVE_KEY = "active"
    POSITION_KEY = "position"
    EXECUTION_ORDER_KEY = "execution_order"
    COMPONENTS_KEY = "components"
    CHILDREN_KEY = "children"
    LINKS_KEY = "links"
    UTIL_OBJECTS_KEY = "util_objects"

    class Roles(enum.IntEnum):
        """Item data roles used to store node state in the stage model."""

        TYPE_ID = QtCore.Qt.UserRole + 1
        TYPE_DISPLAY_NAME = enum.auto()
        TYPE_ICON = enum.auto()
        DESCRIPTION = enum.auto()
        IS_ACTIVE = enum.auto()
        POSITION = enum.auto()
        TAGS = enum.auto()
        IS_LOCKED = enum.auto()
        EXECUTION_STATUS = enum.auto()
        EXECUTION_ORDER = enum.auto()
        RAISED_EXCEPTION = enum.auto()
        SUBTITLE = enum.auto()

    def __init__(
        self,
        name: str | None = None,
        uuid: UUID | str | None = None,
        parent: Node | None = None,
    ) -> None:
        """Initialize Node.

        Args:
            name (str | None): node name. Defaults to the node type's default name.
            uuid (UUID | str | None): node uuid. Generated if omitted.
            parent (Node | None): parent node.
        """
        QtGui.QStandardItem.__init__(self, name or self.DEFAULT_NAME)
        StageObject.__init__(self, uuid=uuid)
        self._set_default_role_values()
        self._components_model = NodeComponentsModel(node=self)
        self._util_objects: dict[UUID, UtilObject] = {}
        self._subtitle_binding: _SubtitleBinding | None = None
        self._components_model.dataChanged.connect(self._on_components_data_changed)

        if parent:
            parent.appendRow(self)

    def setup(self):
        """Create the default components of the node type. Override in subclasses."""
        pass

    def post_setup_hook(self):
        """Run after setup, marking components created by setup as built-in."""
        self._mark_setup_components_as_builtin()

    def _mark_setup_components_as_builtin(self):
        """Mark all current components as built-in, so they can't be removed."""
        for component in self.components_model.list_components():
            component.mark_as_built_in()

    def __repr__(self) -> str:
        """str: node class and path."""
        return f"{inspect_fn.class_string(self.__class__)} ({self.path})"

    def __hash__(self) -> int:
        """int: hash of the node path."""
        return hash(self.path)

    def __getitem__(self, key: str) -> NodeComponent:
        """Get a component by name.

        Args:
            key (str): component name.

        Returns:
            NodeComponent: component with that name.
        """
        return self.components_model.get_component(key)

    def _set_default_role_values(self):
        """Initialize item data roles with the defaults of the node type."""
        self.setData(self.get_type_id(), role=self.Roles.TYPE_ID)
        self.setData(self.get_type_icon(), role=self.Roles.TYPE_ICON)
        self.setData(self.get_description(), role=self.Roles.DESCRIPTION)
        self.setData(True, role=self.Roles.IS_ACTIVE)
        self.setData(QtCore.QPointF(), role=self.Roles.POSITION)
        self.setData(False, role=self.Roles.IS_LOCKED)
        self.setData(self.get_tags(), role=self.Roles.TAGS)
        self.setData(self.get_type_display_name(), role=self.Roles.TYPE_DISPLAY_NAME)
        self.setData(None, role=self.Roles.RAISED_EXCEPTION)
        self.setData(NodeExecutionStatus.NOT_RAN, role=self.Roles.EXECUTION_STATUS)
        self.setData(self.get_type_execution_order(), role=self.Roles.EXECUTION_ORDER)
        self.setData("", role=self.Roles.SUBTITLE)

    @property
    def subtitle(self) -> str:
        """str: extra text shown next to the title of the node, empty for none.

        Not editable by the user and not saved: nodes set it up themselves, either with
        a text or by following a component (see `bind_subtitle_to_component`).
        """
        if self._subtitle_binding is not None:
            return self._subtitle_binding.text(self)
        return self.data(self.Roles.SUBTITLE) or ""

    @subtitle.setter
    def subtitle(self, text: str | None) -> None:
        self._subtitle_binding = None
        self.setData(text or "", role=self.Roles.SUBTITLE)

    def bind_subtitle_to_component(
        self,
        component_name: str,
        formatter: collections.abc.Callable[[NodeComponent], str] | None = None,
    ) -> None:
        """Make the subtitle follow a component of the node.

        The text is worked out whenever it is asked for, and the views are told when
        the value of the component changes. Setting `subtitle` to a text ends the
        binding.

        Args:
            component_name (str): name of the component to follow.
            formatter (Callable[[NodeComponent], str] | None): turns the component into
                the text. Defaults to its display value.
        """
        self._subtitle_binding = _SubtitleBinding(component_name, formatter)
        self.emitDataChanged()

    def _on_components_data_changed(
        self,
        top_left: QtCore.QModelIndex,
        bottom_right: QtCore.QModelIndex,
        roles: list[int],
    ) -> None:
        """Tell the views the subtitle may have changed when its component changed.

        Args:
            top_left (QtCore.QModelIndex): first changed index.
            bottom_right (QtCore.QModelIndex): last changed index.
            roles (list[int]): changed roles, empty for all.
        """
        changed_roles = set(roles)
        for row in range(top_left.row(), bottom_right.row() + 1):
            component = self._components_model.item(row, 0)
            if component is None:
                continue
            if not changed_roles or changed_roles & NodeComponentsModel.EDIT_ROLES:
                self.on_component_edited(component)
            if not changed_roles or (
                NodeComponentsModel.VALUE_CHANGED_ROLE in changed_roles
            ):
                self._notify_linked_targets(component)
            self._update_subtitle_for(component, changed_roles)

    @staticmethod
    def _notify_linked_targets(component: NodeComponent) -> None:
        """Tell the nodes fed by a component that the value they get has changed.

        Args:
            component (NodeComponent): component whose value changed.
        """
        for link in component.output_links:
            target = link.target_component
            if target.node is not component.node:
                target.node.on_component_edited(target)

    def _update_subtitle_for(self, component: NodeComponent, roles: set[int]) -> None:
        """Tell the views the subtitle changed if it follows the changed component.

        Args:
            component (NodeComponent): changed component.
            roles (set[int]): changed roles, empty for all.
        """
        binding = self._subtitle_binding
        if binding is None or component.name != binding.component_name:
            return
        if roles and not roles & set(NodeComponentsModel.VALUE_ROLES):
            return
        self.emitDataChanged()

    def on_component_edited(self, component: NodeComponent) -> None:
        """React to the value or the input links of a component changing.

        Runs for edits from the UI, undo and redo alike, and when execution
        updates the value. Override in subclasses to
        evaluate the node again.

        Args:
            component (NodeComponent): component that changed.
        """

    @property
    def name(self) -> str:
        """Node name

        Returns:
            str: name.

        """
        return self.text()

    @property
    def is_stage_root_node(self):
        """bool: node is the stage root node."""
        return self is self.stage.root_node

    @property
    def scope(self):
        """pathlib.PurePosixPath: path of the parent scope."""
        return tuple(self.path.parents)[0]

    @property
    def path(self) -> pathlib.PurePosixPath:
        """Get current node path.

        Returns:
            pathlib.PurePosixPath: absolute node path.

        """
        path = pathlib.PurePosixPath("/")
        if not self.parent():
            return path / self.name
        return self.parent().path / self.name

    @property
    def stage(self) -> Stage:
        """Utility method pointing to node's stage (model).

        Returns:
            Stage: stage node belongs to.

        """
        return self.model()

    @property
    def components_model(self) -> NodeComponentsModel:
        """Get components model.

        Returns:
            NodeComponentsModel: components model
        """
        return self._components_model

    @property
    def util_objects(self) -> list[UtilObject]:
        """list[UtilObject]: notes, groups and other util objects of the node."""
        return list(self._util_objects.values())

    def add_util_object(self, util_object: UtilObject) -> UtilObject:
        """Add a util object to the node and register it in the stage.

        Args:
            util_object (UtilObject): object to add.

        Returns:
            UtilObject: the added object.
        """
        util_object._node = self
        self._util_objects[util_object.uuid] = util_object
        stage = self.stage
        if stage is not None:
            stage.register_util_object(util_object)
        return util_object

    def remove_util_object(self, util_object: UtilObject) -> None:
        """Remove a util object from the node and unregister it from the stage.

        Args:
            util_object (UtilObject): object to remove.
        """
        self._util_objects.pop(util_object.uuid, None)
        stage = self.stage
        if stage is not None:
            stage.unregister_util_object(util_object)
        util_object._node = None

    def clear_util_objects(self) -> None:
        """Remove all util objects of the node."""
        for util_object in self.util_objects:
            self.remove_util_object(util_object)

    @property
    def locks_children(self) -> bool:
        """bool: the nodes inside can't be changed or linked to from the outside."""
        return NodeFlag.LOCKS_CHILDREN in self.get_type_flags()

    @property
    def locks_structure(self) -> bool:
        """bool: components can't be added, removed, renamed or retyped."""
        return NodeFlag.LOCKS_STRUCTURE in self.get_type_flags()

    @property
    def is_in_locked_scope(self) -> bool:
        """bool: an ancestor owns this node, so it can't be changed from the outside."""
        return any(parent.locks_children for parent in self.list_parents())

    @property
    def is_structure_locked(self) -> bool:
        """bool: the components of the node can't be added, removed or redefined."""
        return self.locks_structure or self.is_in_locked_scope

    @property
    def is_locked(self) -> bool:
        """bool: node can't be modified, by choice or because an ancestor owns it."""
        return bool(self.data(self.Roles.IS_LOCKED)) or self.is_in_locked_scope

    @is_locked.setter
    def is_locked(self, state: bool):
        self.setData(state, self.Roles.IS_LOCKED)

    @property
    def tags(self) -> set[str]:
        """set[str]: node tags."""
        return self.data(role=self.Roles.TAGS)

    @tags.setter
    def tags(self, new_tags: Iterable) -> None:
        self.setData(set(new_tags), role=self.Roles.TAGS)

    @property
    def raised_exception(self) -> Exception | None:
        """Exception | None: exception raised by the last execution."""
        return self.data(self.Roles.RAISED_EXCEPTION)

    @raised_exception.setter
    def raised_exception(self, err: Exception) -> None:
        return self.setData(err, self.Roles.RAISED_EXCEPTION)

    @property
    def execution_order(self) -> NodeExecutionOrderFlag:
        """NodeExecutionOrderFlag: when the node executes relative to its children."""
        return self.data(self.Roles.EXECUTION_ORDER)

    @execution_order.setter
    def execution_order(self, order_flag: NodeExecutionOrderFlag | int) -> None:
        if isinstance(order_flag, int):
            order_flag = NodeExecutionOrderFlag(order_flag)
        self.setData(order_flag, self.Roles.EXECUTION_ORDER)

    @property
    def execution_status(self) -> NodeExecutionStatus:
        """NodeExecutionStatus: status of the last execution."""
        return self.data(self.Roles.EXECUTION_STATUS)

    @execution_status.setter
    def execution_status(self, status: NodeExecutionStatus) -> None:
        self.setData(status, role=self.Roles.EXECUTION_STATUS)

    def reset_execution_status(self):
        """Set the execution status back to not ran."""
        self.execution_status = NodeExecutionStatus.NOT_RAN

    def get_self_driven_flow_components(self) -> tuple[FlowComponent, ...]:
        """Get the flow components the node runs itself while it executes.

        The crawler does not follow them after the node, the node runs their chains
        through `StageCrawler.run_flow_branch` instead.

        Returns:
            tuple[FlowComponent, ...]: self driven flow components, none by default.
        """
        return ()

    def is_active(self) -> bool:
        """Query if node's active state.

        Returns:
            bool: current active state.

        """
        return self.data(role=Node.Roles.IS_ACTIVE)

    def set_active(self, state: bool):
        """Set active state.

        Args:
            state (bool): new active state.

        """
        self.setData(state, role=Node.Roles.IS_ACTIVE)

    def deactivate(self):
        """Set node's active state to False."""
        self.set_active(False)

    def activate(self):
        """Set node's active state to True."""
        self.set_active(True)

    def position(self) -> QtCore.QPointF:
        """QtCore.QPointF: position in the graph."""
        return self.data(role=Node.Roles.POSITION)

    def serializable_position(self):
        """Get the position as plain numbers.

        Returns:
            list[float]: x and y.
        """
        position = self.position()
        return [position.x(), position.y()]

    def set_position(self, position: QtCore.QPointF):
        """Set the position in the graph.

        Args:
            position (QtCore.QPointF): new position.
        """
        self.setData(position, role=Node.Roles.POSITION)

    def appendRow(self, items: Node | typing.Sequence[Node]) -> None:
        """Override Qt method.

        - Generates new unique name.
        - Set cached path to current.
        - Store path into stage path map.

        Args:
            items (typing.Sequence): items to append.

        Raises:
            ValueError: path exists in stage path map.

        """
        if not isinstance(items, typing.Sequence):
            items = [items]

        for node in items:
            unique_name = self.stage.generate_unique_node_name(
                node.name, parent_node=self
            )
            node.setText(unique_name)
            self.stage.register_node(node)
            super().appendRow(node)
            node.setup()
            node.post_setup_hook()

    def rename(self, new_name: str):
        """Rename node.

        - Also update path for self and children in path map.

        Args:
            new_name (str): new node name.

        """
        if new_name == self.name:
            return

        new_name = self.stage.generate_unique_node_name(
            new_name, parent_node=self.parent()
        )
        self.setText(new_name)

    @property
    def child_names_set(self) -> set[str]:
        """Get set of existing child names.

        Returns:
            set[str]: child names.

        """
        return {node.name for node in self.list_children()}

    def list_children(self) -> list[Node]:
        """List child nodes.

        Returns:
            list[Node]: child nodes.

        """
        children = [self.child(row) for row in range(self.rowCount())]
        return children

    def list_children_paths(self) -> list[pathlib.PurePosixPath]:
        """List of child paths.

        Returns:
            list[pathlib.PurePosixPath]: child paths.

        """
        return [child_node.path for child_node in self.list_children()]

    def list_children_tree(self) -> list[Node]:
        """List children tree recursively.

        Returns:
            list[Node]: child nodes tree.

        """
        children = self.list_children()
        for child in children:
            children += child.list_children()
        return children

    def list_parents(self, as_queue: bool = False) -> list[Node] | deque[Node]:
        """List parents recursively.

        Args:
            as_queue: If result should be returned as deque. Defaults to False.

        Returns:
            list[Node] | deque[Node]: parent nodes collection.

        """
        parents = deque()
        direct_parent: Node = self.parent()
        if direct_parent and not direct_parent.is_stage_root_node:
            parents.appendleft(self.parent())
            parents.extendleft(self.parent().list_parents())
        return parents if as_queue else list(parents)

    def delete(self):
        """Delete this node from stage."""
        self.stage.delete_node(self)

    def add_component(self, node_component: NodeComponent):
        """Add a component to the node.

        Args:
            node_component (NodeComponent): component to add.
        """
        self.components_model.add_component(node_component)

    def on_changed(self):
        """Called when the item changes. Override in subclasses."""
        pass

    def get_source_file(self) -> pathlib.Path | None:
        """Get the stage file the contents of the node are loaded from.

        Returns:
            pathlib.Path | None: the file, None if the node isn't loaded from one.
        """
        return None

    def reload_source(self) -> None:
        """Load the contents from the source file again. Override in subclasses."""

    def serialize(
        self, context: NodeSerializationContext | None = None
    ) -> OrderedDict[str, typing.Any]:
        """Serialize node to dict.

        Returns:
            OrderedDict: serialized data

        """
        context = context or NodeSerializationContext(stage=self.stage, entry_node=self)

        serialized_data = super().serialize()
        serialized_data[self.NAME_KEY] = self.name
        serialized_data[self.TYPE_ID_KEY] = self.get_type_id()
        serialized_data[self.ACTIVE_KEY] = self.is_active()
        serialized_data[self.POSITION_KEY] = self.serializable_position()
        serialized_data[self.EXECUTION_ORDER_KEY] = self.execution_order
        serialized_data.update(self.serialize_contents(context))
        self.collect_serialized_links(context)

        if context.entry_node is self:
            serialized_data[Node.LINKS_KEY] = context.get_serialized_links()
        return serialized_data

    def serialize_contents(
        self, context: NodeSerializationContext
    ) -> OrderedDict[str, typing.Any]:
        """Serialize what the node holds: its components and children.

        Override in subclasses that get their contents from somewhere else.

        Args:
            context (NodeSerializationContext): serialization context.

        Returns:
            OrderedDict[str, typing.Any]: data merged into the serialized node.
        """
        contents = OrderedDict(self.components_model.serialize())
        contents[self.CHILDREN_KEY] = [
            child_node.serialize(context=context) for child_node in self.list_children()
        ]
        contents[self.UTIL_OBJECTS_KEY] = [
            util_object.serialize() for util_object in self.util_objects
        ]
        return contents

    def collect_serialized_links(self, context: NodeSerializationContext) -> None:
        """Tell the context which links to store with the node.

        Args:
            context (NodeSerializationContext): serialization context.
        """
        context.collect_links(from_node=self)

    def deserialize_contents(
        self,
        serialized_node: OrderedDict[str, typing.Any],
        context: NodeDeserializationContext,
        restore_uuid: RestoreUuidOption,
    ) -> None:
        """Create the children and components of the node from serialized data.

        Override in subclasses that get their contents from somewhere else.

        Args:
            serialized_node (OrderedDict[str, typing.Any]): serialized node.
            context (NodeDeserializationContext): deserialization context.
            restore_uuid (RestoreUuidOption): how serialized uuids are restored.
        """
        for child_data in serialized_node.get(self.CHILDREN_KEY, {}):
            self.deserialize(
                serialized_node=child_data,
                parent_node=self,
                restore_uuid=restore_uuid,
                context=context,
            )

        self.components_model.deserialize(
            serialized_node.get(self.COMPONENTS_KEY, []),
            context=context,
            restore_uuid=restore_uuid,
        )
        self.deserialize_util_objects(
            serialized_node.get(self.UTIL_OBJECTS_KEY, []),
            context=context,
            restore_uuid=restore_uuid,
        )

    def deserialize_util_objects(
        self,
        util_objects_data: list[OrderedDict[str, typing.Any]],
        context: NodeDeserializationContext,
        restore_uuid: RestoreUuidOption,
    ) -> None:
        """Create util objects from serialized data and add them to the node.

        Args:
            util_objects_data (list[OrderedDict[str, typing.Any]]): serialized objects.
            context (NodeDeserializationContext): deserialization context.
            restore_uuid (RestoreUuidOption): how serialized uuids are restored.
        """
        from .util_object import UtilObject

        for util_object_data in util_objects_data:
            UtilObject.deserialize(
                node=self,
                serialized_data=util_object_data,
                restore_uuid=restore_uuid,
                context=context,
            )

    @classmethod
    def deserialize(
        cls,
        serialized_node: OrderedDict[str, typing.Any],
        node: Node | None = None,
        parent_node: Node | None = None,
        context: NodeDeserializationContext | None = None,
        restore_uuid: RestoreUuidOption = RestoreUuidOption.ATTEMPT_RESTORE,
    ) -> Node:
        """Create or update a node and its contents from serialized data.

        Components, children and links are restored with the node.

        Args:
            serialized_node (OrderedDict[str, typing.Any]): serialized node.
            node (Node | None): existing node to update.
            parent_node (Node | None): parent of the created node.
            context (NodeDeserializationContext | None): deserialization context.
            restore_uuid (RestoreUuidOption): how serialized uuids are restored.

        Returns:
            Node: deserialized node.

        Raises:
            ValueError: if neither node nor parent_node is given.
        """
        if not (node or parent_node):
            raise ValueError(
                "Either parent node or node must be provided for deserialization."
            )

        stage = parent_node.stage if parent_node else node.stage
        uuid = cls.choose_new_uuid(
            stage=stage,
            serialized_data=serialized_node,
            restore_option=restore_uuid,
        )

        if not node:
            node_cls = NYX_REGISTRY.get_node_cls(serialized_node[cls.TYPE_ID_KEY])
            node = node_cls(
                name=serialized_node[cls.NAME_KEY], uuid=uuid, parent=parent_node
            )
        else:
            node.rename(serialized_node[cls.NAME_KEY])

        context = context or NodeDeserializationContext(
            stage=stage,
            entry_node=node,
        )
        if context.entry_node is None:
            context.entry_node = node

        LOGGER.debug(f"Deserializing: {serialized_node.get(cls.NAME_KEY)}")
        if uuid is not None:
            node.uuid = uuid
        node.restore_graphics_object_id(serialized_node)

        context.register(
            serialized_uuid=serialized_node[cls.UUID_KEY], new_uuid=node.uuid
        )
        links_data = serialized_node.get(cls.LINKS_KEY, [])

        # Roles that should exist for normal and reference nodes
        node.set_active(serialized_node.get(cls.ACTIVE_KEY, True))
        node.set_position(
            QtCore.QPointF(*serialized_node.get(cls.POSITION_KEY, [0.0, 0.0]))
        )
        node.execution_order = serialized_node.get(
            cls.EXECUTION_ORDER_KEY, cls.get_type_execution_order()
        )

        node.deserialize_contents(
            serialized_node, context=context, restore_uuid=restore_uuid
        )
        stage.register_node(node)

        # Links
        if context.defer_links:
            context.collect_links(links_data)
        elif context.entry_node is node:
            node.deserialize_links(
                links_data=links_data, restore_uuid=restore_uuid, context=context
            )

        # Everything this run creates exists now: let object paths find their targets.
        # With deferred links the caller owns the run and does it once all is created.
        if context.entry_node is node and not context.defer_links:
            context.run_deferred()

        return node

    def deserialize_links(
        self,
        links_data: list[OrderedDict[str, typing.Any]],
        restore_uuid: RestoreUuidOption,
        context: NodeDeserializationContext,
    ):
        """Create links from serialized data.

        Args:
            links_data (list[OrderedDict[str, typing.Any]]): serialized links.
            restore_uuid (RestoreUuidOption): how serialized uuids are restored.
            context (NodeDeserializationContext): deserialization context.
        """
        for each_link_data in links_data:
            link_data = context.remap_link(each_link_data)
            if link_data is None:
                continue
            link = Link.deserialize(
                stage=self.stage,
                serialized_link=link_data,
                link=None,
                restore_uuid=restore_uuid,
            )
            self.stage.register_link(link)

    def export_to_json(self, file_path: pathlib.Path):
        """Export node to json file.

        Args:
            file_path (pathlib.Path): json file path.

        """
        data = self.serialize()
        file_fn.write_json(file_path, data)

    def load_from_json(self, file_path: pathlib.Path):
        """Load the contents of a json file into this node.

        Args:
            file_path (pathlib.Path): json file path.

        """
        json_data = file_fn.load_json(file_path, object_pairs_hook=OrderedDict)
        self.deserialize(json_data, node=self)

    def find_child_by_name(self, name) -> Node | None:
        """Find a direct child by name.

        Args:
            name (str): child name.

        Returns:
            Node | None: child, None if not found.
        """
        for node in self.list_children():
            if node.name == name:
                return node

    def find_child_node_of_type(self, type_id: str) -> Node | None:
        """Find the first direct child of a type.

        Args:
            type_id (str): node type id.

        Returns:
            Node | None: child, None if not found.
        """
        for node in self.list_children():
            if node.get_type_id() == type_id:
                return node

    def find_flow_start_node(self) -> FlowStartNode:
        """Find first child flow start node

        Returns:
            FlowStartNode instance.
        """
        return self.find_child_node_of_type(type_id=CoreNodes.FLOW_START)

    def accept_visitor(self, visitor: NodeVisitor):
        """Let a visitor visit this node. Inactive nodes are skipped.

        Args:
            visitor (NodeVisitor): visitor.
        """
        if not self.is_active():
            LOGGER.warning("Not Active: %s", self.path.as_posix())
            return
        visitor.visit_node(self)

    def pre_execution(self):
        """Clear the raised exception before executing."""
        self.setData(None, self.Roles.RAISED_EXCEPTION)

    def pre_execution_hook(self):
        """Called before execution. Override in subclasses."""
        pass

    def post_execution_hook(self):
        """Called after execution. Override in subclasses."""
        pass

    def evaluate(self):
        """Evaluate components values on this node.

        Raises:
            err: run time exception raised during code execution.

        """
        pass

    def execute(self):
        """Run the node logic. Override in subclasses."""
        pass

    def evaluate_components(self):
        """Run the evaluation hook of every component."""
        for component in self.components_model.list_components():
            component.evaluation_hook()

    def execute_components(self):
        """Run the execution hook of every component."""
        for component in self.components_model.list_components():
            component.execution_hook()

    def execution_hook(self):
        """Execute this node.

        Raises:
            err: run time exception raised during code execution.

        """
        self.reset_execution_status()
        if not self.is_active():
            return

        self.execution_status = NodeExecutionStatus.PENDING
        start_time = time.perf_counter()
        try:
            self.pre_execution_hook()
            self.evaluate_components()
            self.evaluate()
            self.execute_components()
            self.execute()
            self.post_execution_hook()
        except Exception as err:
            LOGGER.exception(f"{self} | Execution error: {err}")
            self.raised_exception = err
            self.execution_status = NodeExecutionStatus.ERROR
            self.stage.execution_failed.emit(self)
            raise err
        else:
            self.execution_status = NodeExecutionStatus.SUCCESS

        total_time = time.perf_counter() - start_time
        LOGGER.info(f"Executed in {total_time:.4f}: {self.path}")

    @classmethod
    def get_type_id(cls) -> str:
        """str: unique type id. Subclasses must implement."""
        raise NotImplementedError

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI. Subclasses must implement."""
        raise NotImplementedError

    @classmethod
    def get_type_flags(cls) -> NodeFlag:
        """NodeFlag: what nodes of the type allow. Subclasses add to the parent flags."""
        return NodeFlag.NONE

    @classmethod
    def get_type_execution_order(cls) -> NodeExecutionOrderFlag:
        """NodeExecutionOrderFlag: default execution order of the node type."""
        return NodeExecutionOrderFlag.BEFORE_CHILDREN

    @classmethod
    def get_render_options(cls) -> NodeRenderOptions:
        """Get the options the editor draws nodes of this type with.

        Subclasses can take the options of their parent class, change what they want
        and return them.

        Returns:
            NodeRenderOptions: new options with the default values.
        """
        return NodeRenderOptions()

    @classmethod
    def get_tags(cls) -> set[str]:
        """set[str]: default tags of the node type."""
        return set()
