import logging

from PySide6 import QtCore

from ...core.node import Node
from ...core.commands import CreateNodeCommand
from .stage_object_spawner import StageObjectSpawner

LOGGER = logging.getLogger(__name__)


class NodeSpawner(StageObjectSpawner):
    """Creates the nodes the user picks in the nodes palette, in the scope being drawn.

    Attributes:
        nodeSpawned: emitted with the node that was created.
    """

    nodeSpawned = QtCore.Signal(Node)

    def __init__(self, parent=None):
        """Initialize NodeSpawner.

        Args:
            parent (QtCore.QObject | None): parent object.
        """
        super().__init__(parent)
        self._spawn_position: QtCore.QPointF | None = None

    @property
    def spawn_position(self) -> QtCore.QPointF | None:
        """QtCore.QPointF | None: scene position new nodes are created at."""
        return self._spawn_position

    @spawn_position.setter
    def spawn_position(self, position: QtCore.QPointF | None) -> None:
        if position is None:
            self._spawn_position = None
            return

        if not isinstance(position, QtCore.QPointF):
            raise TypeError(
                f"Spawn position can be of type QPointF or None, got {type(position)}"
            )
        self._spawn_position = position

    @QtCore.Slot(str, result=Node)
    def spawnNodeAtCenter(self, type_id: str) -> Node:
        """Create a node at the center of the active view.

        Args:
            type_id (str): registered node type id.

        Returns:
            Node: created node.
        """
        self.spawn_position = None
        return self.spawnNode(type_id=type_id, position=None)

    @QtCore.Slot(str, result=Node)
    def spawnNode(self, type_id: str, position: QtCore.QPointF | None = None):
        """Create a node in the current scope through an undoable command.

        Args:
            type_id (str): registered node type id.
            position (QtCore.QPointF | None): scene position. Defaults to the spawn
                position or view center.

        Returns:
            Node | None: created node, None if there is no editor or the stage refused
                the node, for example in a scope that is locked.
        """
        current_editor = self.current_stage_graph
        if current_editor is None:
            return None

        position = (
            position
            or self.spawn_position
            or current_editor.gr_view.get_center_position()
        )

        stage = current_editor.stage
        command = CreateNodeCommand(
            stage=stage,
            type_id=type_id,
            parent_node=current_editor.get_scope_path(),
            position=position,
        )
        result_node = self._spawn(stage, command, lambda: command.result_node)
        if result_node is not None:
            self.nodeSpawned.emit(result_node)
        return result_node
