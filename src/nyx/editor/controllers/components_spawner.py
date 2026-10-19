import logging

from PySide6 import QtCore

from ...core.node import Node
from ...core.node_component import NodeComponent
from ...core.commands import AddNodeComponentCommand


LOGGER = logging.getLogger(__name__)


class NodeComponentSpawner(QtCore.QObject):
    """Owns selection state for a components model and keeps it
    consistent across reorders."""

    componentSpawned = QtCore.Signal(NodeComponent)

    @QtCore.Slot(str, "QVariant", result="QVariant")
    def spawnComponent(self, type_id: str, target_node: Node):
        """Add a component to a node through an undoable command.

        Args:
            type_id (str): registered component type id.
            target_node (Node): node receiving the component.

        Returns:
            NodeComponent: created component.
        """
        command = AddNodeComponentCommand(node=target_node, type_id=type_id)
        target_node.stage.push_command(command)
        result_component = command.result_component
        self.componentSpawned.emit(result_component)
        return result_component
