import logging

from PySide6 import QtCore

from ...core.node import Node
from ...core.node_component import NodeComponent
from ...core.commands import AddNodeComponentCommand
from .stage_object_spawner import StageObjectSpawner


LOGGER = logging.getLogger(__name__)


class NodeComponentSpawner(StageObjectSpawner):
    """Adds the components the user picks in the components list to a node.

    Attributes:
        componentSpawned: emitted with the component that was added.
    """

    componentSpawned = QtCore.Signal(NodeComponent)

    @QtCore.Slot(str, "QVariant", result="QVariant")
    def spawnComponent(self, type_id: str, target_node: Node):
        """Add a component to a node through an undoable command.

        Args:
            type_id (str): registered component type id.
            target_node (Node): node receiving the component.

        Returns:
            NodeComponent | None: created component, None if the node refused it.
        """
        command = AddNodeComponentCommand(node=target_node, type_id=type_id)
        result_component = self._spawn(
            target_node.stage, command, lambda: command.result_component
        )
        if result_component is not None:
            self.componentSpawned.emit(result_component)
        return result_component
