import dataclasses
import typing
import logging
from PySide6 import QtGui, QtCore
from collections import OrderedDict
from collections.abc import Iterator
from uuid import UUID

from ..node_component import NodeComponent
from ..datatypes.datatype import value_to_view_text
from ..contexts.serialization import NodeDeserializationContext
from ..plugin_subsystem.registry import NYX_REGISTRY
from ...static.enums import CoreNodeComponents, RestoreUuidOption
from ...utils import names_fn


if typing.TYPE_CHECKING:
    from ..node import Node
    from nyx.plugins.core.node_components.flow import FlowComponent


LOGGER = logging.getLogger(__name__)


@dataclasses.dataclass(eq=False)
class _Dependency:
    """A component that has to be refreshed when another one changes.

    Attributes:
        dependent: component to refresh
        source: component it depends on
        when: roles of the source that trigger the refresh
        refresh: roles of the dependent to report as changed
    """

    dependent: NodeComponent
    source: NodeComponent
    when: frozenset[int]
    refresh: tuple[int, ...]


class NodeComponentsModel(QtGui.QStandardItemModel):
    """Item model holding the components of a node."""

    # Roles that describe the value of a component, and what views show of it.
    VALUE_ROLES = (
        NodeComponent.Roles.RAW_VALUE,
        NodeComponent.Roles.CACHED_VALUE,
        NodeComponent.Roles.DISPLAY_VALUE,
        NodeComponent.Roles.IS_VALID,
    )

    # Roles whose change means the value or the links of a component changed, see
    # `Node.on_component_edited`. The cached value is the last one a push writes.
    EDIT_ROLES = frozenset(
        (NodeComponent.Roles.CACHED_VALUE, NodeComponent.Roles.INPUT_LINKS)
    )

    VALUE_CHANGED_ROLE = NodeComponent.Roles.CACHED_VALUE

    def __init__(self, node: Node):
        """Initialize NodeComponentsModel.

        Args:
            node (Node): node owning the components.
        """
        self._node = node
        self._dependencies: list[_Dependency] = []
        self._propagating: set[int] = set()
        super().__init__()
        self._register_qml_role_names()
        self.dataChanged.connect(self._refresh_dependents)

    @property
    def node(self) -> Node:
        """Node: node owning the components."""
        return self._node

    def _register_qml_role_names(self) -> None:
        """Expose NodeComponent roles to QML by name."""
        names = dict(self.roleNames())
        names.update(names_fn.enum_to_dict(NodeComponent.Roles))  # ty: ignore
        self.setItemRoleNames(names)

    def add_dependency(
        self,
        dependent: NodeComponent,
        on: NodeComponent,
        when: typing.Iterable[int] = VALUE_ROLES,
        refresh: typing.Iterable[int] = (
            NodeComponent.Roles.CACHED_VALUE,
            NodeComponent.Roles.DISPLAY_VALUE,
            NodeComponent.Roles.IS_VALID,
        ),
    ) -> None:
        """Refresh a component whenever another component of the node changes.

        Meant for `Node.setup`, for components whose value is worked out from other
        components. The views are told that the dependent changed, so they ask it for
        its value again. The dependent can have dependents of its own, and cycles are
        cut instead of followed.

        Args:
            dependent (NodeComponent): component to refresh.
            on (NodeComponent): component it depends on.
            when (Iterable[int]): roles of `on` that trigger the refresh. An empty
                value means any change.
            refresh (Iterable[int]): roles of the dependent to report as changed.
        """
        self._dependencies.append(
            _Dependency(
                dependent=dependent,
                source=on,
                when=frozenset(when),
                refresh=tuple(refresh),
            )
        )

    def remove_dependencies(self, component: NodeComponent) -> None:
        """Forget every dependency that involves a component.

        Args:
            component (NodeComponent): component that is the source or the dependent.
        """
        self._dependencies = [
            dependency
            for dependency in self._dependencies
            if component not in (dependency.dependent, dependency.source)
        ]

    def _refresh_dependents(
        self,
        top_left: QtCore.QModelIndex,
        bottom_right: QtCore.QModelIndex,
        roles: typing.Sequence[int] = (),
    ) -> None:
        """Report a change to the components that depend on the changed ones.

        Args:
            top_left (QtCore.QModelIndex): first changed index.
            bottom_right (QtCore.QModelIndex): last changed index.
            roles (Sequence[int]): changed roles, empty if everything changed.
        """
        if not self._dependencies:
            return

        changed_roles = set(roles)
        for row in range(top_left.row(), bottom_right.row() + 1):
            source = self.item(row)
            if source is None or id(source) in self._propagating:
                continue

            triggered = [
                dependency
                for dependency in self._dependencies
                if dependency.source is source
                and (
                    not dependency.when
                    or not changed_roles
                    or changed_roles & dependency.when
                )
            ]
            self._propagating.add(id(source))
            try:
                for dependency in triggered:
                    index = dependency.dependent.index()
                    if dependency.dependent.model() is self and index.isValid():
                        self.dataChanged.emit(index, index, list(dependency.refresh))
            finally:
                self._propagating.discard(id(source))

    def data(
        self,
        index: QtCore.QModelIndex,
        role: QtCore.Qt.ItemDataRole = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> typing.Any:
        """Get item data, resolving virtual roles from the component.

        Args:
            index (QtCore.QModelIndex): item index.
            role (QtCore.Qt.ItemDataRole): data role.

        Returns:
            typing.Any: role data.
        """
        if not index.isValid():
            return

        if role in NodeComponent.Roles.virtual_roles():
            component: NodeComponent = self.itemFromIndex(index)
            if role == NodeComponent.Roles.UUID:
                return str(component.uuid)
            if role == NodeComponent.Roles.PATH:
                return component.path.as_posix()
            if role == NodeComponent.Roles.DISPLAY_VALUE:
                return component.get_display_value()
            if role == NodeComponent.Roles.NODE:
                return self.node
            if role == NodeComponent.Roles.INPUT_LINKS:
                return [
                    str(link.source_component.path) for link in component.input_links
                ]
            if role == NodeComponent.Roles.OUTPUT_LINKS:
                return [
                    str(link.target_component.path) for link in component.output_links
                ]
            if role == NodeComponent.Roles.EDITOR_QML_FILE:
                return component.get_qml_editor_url()
            if role == NodeComponent.Roles.IS_EDITABLE:
                return component.is_editable
            if role == NodeComponent.Roles.IS_VALID:
                return component.is_valid
            if role == NodeComponent.Roles.RESOLVED_DATATYPE:
                return component.resolved_datatype_id
            if role == NodeComponent.Roles.IS_DATATYPE_LOCKED:
                return component.is_datatype_locked
            if role == NodeComponent.Roles.IS_BUILT_IN:
                return component.is_built_in
            if role == NodeComponent.Roles.IS_STATIC:
                return component.is_static
            if role == NodeComponent.Roles.WRITABLE:
                return component.writable
            if role == NodeComponent.Roles.READABLE:
                return component.readable
            else:
                LOGGER.error(f"No value defined for virtual role: {role}")
                return None

        value = super().data(index, role)

        if role in (
            NodeComponent.Roles.RAW_VALUE,
            NodeComponent.Roles.CACHED_VALUE,
            NodeComponent.Roles.DEFAULT_VALUE,
        ):
            # The views can't show classes or collections, they get text
            return value_to_view_text(value)
        if role == NodeComponent.Roles.LINKS:
            return [str(uuid) for uuid in (value or ())]
        if role == NodeComponent.Roles.TAGS:
            return sorted(value or ())
        if role == NodeComponent.Roles.COMPONENT_FLAGS:
            return int(getattr(value, "value", value) or 0)
        return value

    @QtCore.Slot(int, int, int, result=bool)
    def move(self, from_row: int, to_row: int, count: int = 1) -> bool:
        """Move a component to another row. Built-in components can't be moved.

        Args:
            from_row (int): current row.
            to_row (int): destination row.
            count (int): unused, a single row is moved.

        Returns:
            bool: component was moved.
        """
        n = self.rowCount()
        if from_row == to_row or not (0 <= from_row < n) or not (0 <= to_row < n):
            return False

        root: QtGui.QStandardItem = self.invisibleRootItem()
        if root.child(from_row).is_built_in or root.child(to_row).is_built_in:
            return False

        items = self.takeRow(from_row)
        self.insertRow(to_row, items)
        return True

    def list_components(self, type_id_filter: str | None = None) -> list[NodeComponent]:
        """List the components of the node.

        Args:
            type_id_filter (str | None): only list components of this type id.

        Returns:
            list[NodeComponent]: components in row order.
        """
        all_components: list[NodeComponent] = [
            self.invisibleRootItem().child(row)
            for row in range(self.invisibleRootItem().rowCount())
        ]
        if type_id_filter is None:
            return all_components
        return [
            component
            for component in all_components
            if component.get_type_id() == type_id_filter
        ]

    def serialize(self):
        """Serialize all components.

        Returns:
            OrderedDict: data with a "components" list.
        """
        data = OrderedDict()
        components = self.list_components()
        serialized_components = [
            each_component.serialize() for each_component in components
        ]
        data["components"] = serialized_components
        return data

    def deserialize(
        self,
        data: list[dict],
        context: NodeDeserializationContext,
        restore_uuid: RestoreUuidOption = RestoreUuidOption.ATTEMPT_RESTORE,
    ):
        """Create or update components from serialized data.

        Args:
            data (list[dict]): serialized components.
            context (NodeDeserializationContext): deserialization context.
            restore_uuid (RestoreUuidOption): how serialized uuids are restored.
        """
        for component_data in data:
            try:
                component = self.get_component(component_data["name"])
            except ValueError:
                component = None

            component_exists = component is not None
            component = NodeComponent.deserialize(
                data=component_data,
                node=self.node,
                context=context,
                component=component,
                restore_uuid=restore_uuid,
            )
            if not component_exists:
                self.appendRow(component)

    def create_component(
        self, type_id: str, uuid: UUID | str | None = None
    ) -> NodeComponent:
        """Instantiate a registered component type without adding it.

        Args:
            type_id (str): registered component type id.
            uuid (UUID | str | None): uuid for the component.

        Returns:
            NodeComponent: new component.
        """
        component_cls = NYX_REGISTRY.get_node_component_cls(type_id=type_id)
        return component_cls(uuid=uuid)

    def add_component(self, component: NodeComponent, at_row: int | None = None):
        """Add a component, making its name unique.

        Args:
            component (NodeComponent): component to add.
            at_row (int | None): row to insert at. Appended if omitted.
        """
        component.name = self.compose_unique_component_name(component.name)
        if at_row is not None:
            self.insertRow(at_row, component)
        else:
            self.appendRow(component)

        if self.node.stage:
            self.node.stage.uuid_map[component.uuid] = component
        LOGGER.debug(f"Added new component: {component}")

    def remove_component(self, uuid: UUID, force: bool = False) -> None:
        """Remove a component from the node.

        Args:
            uuid (UUID): uuid of the component.
            force (bool): remove built-in components too, for the node owning them.

        Raises:
            ValueError: if the component doesn't exist or is built-in.
        """
        component = self.node.stage.get_object(uuid)
        if component is None:
            raise ValueError(f"Component UUID doesn't exist in stage: {uuid}")

        if component.is_built_in and not force:
            raise ValueError(f"Can't remove builtin component: {component.path}")

        if self.node.stage:
            self.node.stage.uuid_map.pop(component.uuid)
        self.remove_dependencies(component)
        self.removeRow(component.row())

    def remove_component_by_name(self, name: str) -> None:
        """Remove components with the given name.

        Args:
            name (str): component name.
        """
        for component in self.list_components():
            if component.name != name:
                continue
            self.remove_component(component.uuid)

    def compose_unique_component_name(self, name: str) -> str:
        """Returns a unique name for the component, indexed if it already exists."""
        existing_names = [component.name for component in self.list_components()]
        index = 1
        result_name = name
        while name in existing_names:
            name = f"{result_name}{index}"
            index += 1

        return name

    def get_component(self, name: str) -> NodeComponent:
        """Get component from name.

        Args:
            name: component name

        Returns:
            NodeComponent instance if found, otherwise None
        """
        name = name.removeprefix(".")
        hits = self.match(
            self.index(0, 0),
            NodeComponent.Roles.NAME,
            name,
            hits=-1,
            flags=QtCore.Qt.MatchFlag.MatchExactly,
        )
        result_items = (self.itemFromIndex(index) for index in hits)
        component = next(result_items, None)
        if not component:
            raise ValueError(f"{self.node} has no component: {name}")
        return component

    def find_writable_flow_components(self) -> Iterator[FlowComponent]:
        """Find active flow components that accept input.

        Yields:
            FlowComponent: matching flow components.
        """
        for flow_component in self.find_components_of_type(CoreNodeComponents.FLOW):
            if flow_component.is_active and flow_component.writable:
                yield flow_component  # ty: ignore

    def find_readable_flow_components(self) -> Iterator[FlowComponent]:
        """Find active flow components that produce output.

        Yields:
            FlowComponent: matching flow components.
        """
        for flow_component in self.find_components_of_type(CoreNodeComponents.FLOW):
            if flow_component.is_active and flow_component.readable:
                yield flow_component  # ty: ignore

    def find_components_of_type(self, type_id: str) -> Iterator[NodeComponent]:
        """Find components of a registered type.

        Args:
            type_id (str): registered component type id.

        Yields:
            NodeComponent: components of that type.

        Raises:
            TypeError: if the type isn't registered.
        """
        component_cls: NodeComponent = NYX_REGISTRY.get_node_component_cls(type_id)
        if not component_cls:
            raise TypeError(
                f"Component of type {type_id} is not found in NYX_REGISTRY."
                f"Available types: {NYX_REGISTRY.node_components.keys()}"
            )
        for row in range(self.rowCount()):
            component: NodeComponent = self.item(row, 0)
            if isinstance(component, component_cls):
                yield component
