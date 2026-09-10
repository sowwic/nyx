import typing
import logging
from PySide6 import QtGui

from ..serializable import Serializable
from ._base_component import NodeComponent
from ..plugin_subsystem.registry import NYX_REGISTRY


if typing.TYPE_CHECKING:
    from ..node import Node


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
            component = NodeComponent()
            self.appendRow(component)
            component.deserialize(component_data)

    def create_component(self, type_id: str) -> NodeComponent:
        component_cls = NYX_REGISTRY.get_node_component_cls(type_id=type_id)
        return component_cls()

    def add_component(self, component: NodeComponent):
        component.name = self.get_unique_component_name(component.name)
        self.appendRow(component)
        LOGGER.debug(f"Added new component: {component}")

    def remove_component(self, name: str):
        for component in self.list_components():
            if component.name == name:
                self.removeRow(component.row())
                return

    def get_unique_component_name(self, name: str) -> str:
        """Returns a unique name for the component, indexed if it already exists."""
        existing_names = [component.name for component in self.list_components()]
        index = 1
        while name in existing_names:
            name = f"{name}{index}"
            index += 1

        return name
