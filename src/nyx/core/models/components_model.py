import typing
import logging
from PySide6 import QtGui, QtCore
from collections import OrderedDict
from collections.abc import Iterator
from uuid import UUID

from ..node_component import NodeComponent
from ..contexts.serialization import NodeDeserializationContext
from ..plugin_subsystem.registry import NYX_REGISTRY
from ...static.enums import CoreNodeComponents, RestoreUuidOption
from ...utils import names_fn


if typing.TYPE_CHECKING:
    from ..node import Node
    from nyx.plugins.core.node_components.flow import FlowComponent


LOGGER = logging.getLogger(__name__)


class NodeComponentsModel(QtGui.QStandardItemModel):
    def __init__(self, node: Node):
        self._node = node
        super().__init__()
        self._register_qml_role_names()

    @property
    def node(self) -> Node:
        return self._node

    def _register_qml_role_names(self) -> None:
        names = dict(self.roleNames())
        names.update(names_fn.enum_to_dict(NodeComponent.Roles))  # ty: ignore
        self.setItemRoleNames(names)

    def data(
        self,
        index: QtCore.QModelIndex,
        role: QtCore.Qt.ItemDataRole = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> typing.Any:
        if not index.isValid():
            return

        if role in NodeComponent.Roles.virtual_roles():
            component: NodeComponent = self.itemFromIndex(index)
            if role == NodeComponent.Roles.UUID:
                return str(component.uuid)
            if role == NodeComponent.Roles.PATH:
                return component.path.as_posix()
            if role == NodeComponent.Roles.EDITOR_QML_FILE:
                return component.get_qml_editor_url()
            if role == NodeComponent.Roles.IS_EDITABLE:
                return component.is_editable
            if role == NodeComponent.Roles.IS_BUILT_IN:
                return component.is_built_in
            if role == NodeComponent.Roles.IS_STATIC:
                return component.is_static
            else:
                LOGGER.error(f"No value defined for virtual role: {role}")
                return None

        value = super().data(index, role)

        if role == NodeComponent.Roles.LINKS:
            return [str(uuid) for uuid in (value or ())]
        if role == NodeComponent.Roles.TAGS:
            return sorted(value or ())
        if role == NodeComponent.Roles.COMPONENT_FLAGS:
            return int(getattr(value, "value", value) or 0)
        return value

    @QtCore.Slot(int, int, int, result=bool)
    def move(self, from_row: int, to_row: int, count: int = 1) -> bool:
        n = self.rowCount()
        if from_row == to_row or not (0 <= from_row < n) or not (0 <= to_row < n):
            return False

        root: QtGui.QStandardItem = self.invisibleRootItem()
        if root.child(from_row).is_built_in or root.child(to_row).is_built_in:
            return False

        dest = to_row + 1 if to_row > from_row else to_row

        if not self.beginMoveRows(
            QtCore.QModelIndex(), from_row, from_row, QtCore.QModelIndex(), dest
        ):
            return False

        # Reorder the real rows, but suppress the remove/insert signals so views
        # only see the single "rows moved" notification.
        self.blockSignals(True)
        try:
            items = self.takeRow(from_row)
            self.insertRow(to_row, items)
        finally:
            self.blockSignals(False)

        self.endMoveRows()
        return True

    def list_components(self, type_id_filter: str | None = None) -> list[NodeComponent]:
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

    def create_component(self, type_id: str) -> NodeComponent:
        component_cls = NYX_REGISTRY.get_node_component_cls(type_id=type_id)
        return component_cls()

    def add_component(self, component: NodeComponent, at_row: int | None = None):
        component.name = self.compose_unique_component_name(component.name)
        if at_row:
            self.insertRow(at_row, component)
        else:
            self.appendRow(component)

        if self.node.stage:
            self.node.stage.uuid_map[component.uuid] = component
        LOGGER.debug(f"Added new component: {component}")

    def remove_component(self, uuid: UUID) -> None:
        component = self.node.stage.get_object(uuid)
        if component is None:
            raise ValueError(f"Component UUID doesn't exist in stage: {uuid}")

        if component.is_built_in:
            LOGGER.error(f"Can't remove builtin component: {component.path}")
            return

        if self.node.stage:
            self.node.stage.uuid_map.pop(component.uuid)
        self.removeRow(component.row())

    def remove_component_by_name(self, name: str) -> None:
        for component in self.list_components():
            if component.name != name:
                continue
            self.remove_component(component.uuid)

    def compose_unique_component_name(self, name: str) -> str:
        """Returns a unique name for the component, indexed if it already exists."""
        existing_names = [component.name for component in self.list_components()]
        index = 1
        while name in existing_names:
            name = f"{name}{index}"
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
        for flow_component in self.find_components_of_type(CoreNodeComponents.FLOW):
            if flow_component.is_active and flow_component.accepts_input:
                yield flow_component  # ty: ignore

    def find_readable_flow_components(self) -> Iterator[FlowComponent]:
        for flow_component in self.find_components_of_type(CoreNodeComponents.FLOW):
            if flow_component.is_active and flow_component.produces_output:
                yield flow_component  # ty: ignore

    def find_components_of_type(self, type_id: str) -> Iterator[NodeComponent]:
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
