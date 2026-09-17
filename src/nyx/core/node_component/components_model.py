import typing
import logging
from PySide6 import QtGui, QtCore
from collections.abc import Iterator

from ..serializable import Serializable
from ._base_component import NodeComponent
from ..plugin_subsystem.registry import NYX_REGISTRY
from ...static.enums import CoreNodeComponents


if typing.TYPE_CHECKING:
    from ..node import Node
    from nyx.plugins.core.node_components.flow import FlowComponent


LOGGER = logging.getLogger(__name__)


class NodeComponentsModel(QtGui.QStandardItemModel, Serializable):
    def __init__(self, node: Node):
        self._node = node
        QtGui.QStandardItemModel.__init__(self)
        Serializable.__init__(self)

    @property
    def node(self) -> Node:
        return self._node

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
            if component.TYPE_ID == type_id_filter
        ]

    def serialize(self):
        data = Serializable.serialize(self)
        components = self.list_components()
        serialized_components = [
            each_component.serialize() for each_component in components
        ]
        data["components"] = serialized_components
        # TODO: serialized components into a list of dicts

        return data

    def deserialize(self, data: list[dict]):
        super().deserialize(data)
        # Deserialize components
        for component_data in data:
            component = self.get_component(component_data["name"])
            if component is None:
                component = self.create_component(component_data["type_id"])
                self.appendRow(component)
            component.deserialize(component_data)

    def create_component(self, type_id: str) -> NodeComponent:
        component_cls = NYX_REGISTRY.get_node_component_cls(type_id=type_id)
        return component_cls()

    def add_component(self, component: NodeComponent):
        component.name = self.compose_unique_component_name(component.name)
        self.appendRow(component)
        LOGGER.debug(f"Added new component: {component}")

    def remove_component(self, name: str) -> None:
        for component in self.list_components():
            if component.name != name:
                continue

            if component.is_built_in:
                LOGGER.error(f"Can't remove builtin component: {component.as_path()}")
                return
            self.removeRow(component.row())

    def compose_unique_component_name(self, name: str) -> str:
        """Returns a unique name for the component, indexed if it already exists."""
        existing_names = [component.name for component in self.list_components()]
        index = 1
        while name in existing_names:
            name = f"{name}{index}"
            index += 1

        return name

    def get_component(self, name: str) -> NodeComponent | None:
        """Get component from name.

        Args:
            name: component name

        Returns:
            NodeComponent instance if found, otherwise None
        """
        hits = self.match(
            self.index(0, 0),
            NodeComponent.Roles.NAME,
            name,
            hits=-1,
            flags=QtCore.Qt.MatchFlag.MatchExactly,
        )
        result_items = (self.itemFromIndex(index) for index in hits)
        return next(result_items, None)

    # TODO: Generic function
    def find_writable_flow_components(self) -> Iterator[FlowComponent]:
        for flow_component in self.find_components_of_type(CoreNodeComponents.FLOW):
            if flow_component.is_active and flow_component.is_writable:
                yield flow_component

    def find_readable_flow_components(self) -> Iterator[FlowComponent]:
        for flow_component in self.find_components_of_type(CoreNodeComponents.FLOW):
            if flow_component.is_active and flow_component.is_readable:
                yield flow_component

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
