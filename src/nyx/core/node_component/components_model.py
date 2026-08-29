import typing
from PySide6 import QtGui

from ..serializable import Serializable
from ._base_component import NodeComponent


if typing.TYPE_CHECKING:
    pass


class NodeComponentsModel(QtGui.QStandardItemModel, Serializable):
    def __init__(self, node):
        self._node = node
        QtGui.QStandardItemModel.__init__(self)
        Serializable.__init__(self)

    @property
    def node(self):
        return self._node

    def list_components(self):
        return [
            self.invisibleRootItem().child(row)
            for row in range(self.invisibleRootItem().rowCount())
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

    def add_component(self, component: NodeComponent):
        self.appendRow(component)

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
