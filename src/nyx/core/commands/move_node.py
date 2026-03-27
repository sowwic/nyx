import logging
import pathlib
from collections import deque

from PySide6 import QtCore
from PySide6 import QtGui

from nyx.core import Node
from nyx.core import Stage
from ._base_nyx_command import NyxCommand

LOGGER = logging.getLogger(__name__)


class MoveNodeCommand(NyxCommand):
    def __init__(
        self,
        stage: Stage,
        nodes: list[Node] | list[pathlib.PurePosixPath] | list[str],
        new_positions: list[QtCore.QPointF],
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        super().__init__(stage, "Moved nodes", parent)
        if not isinstance(nodes, (list, tuple, deque)):
            nodes = [nodes]
        if not isinstance(new_positions, (list, tuple, deque)):
            new_positions = [new_positions]

        self.node_paths = [self.stage.node(node).path for node in nodes]
        self.old_positions = [self.stage.node(node).position() for node in nodes]
        self.new_positions = new_positions

        self.setText(f"{self.text()} {[p.as_posix() for p in self.node_paths]}")

    def redo(self) -> None:
        for node, new_pos in zip(
            [self.stage.node(path) for path in self.node_paths], self.new_positions
        ):
            node.set_position(new_pos)
            if node.gr_node and node.gr_node.pos() != new_pos:
                node.gr_node.setPos(new_pos)

        return super().redo()

    def undo(self) -> None:
        for node, old_pos in zip(
            [self.stage.node(path) for path in self.node_paths], self.old_positions
        ):
            node.set_position(old_pos)
            if node.gr_node and node.gr_node.pos() != old_pos:
                node.gr_node.setPos(old_pos)
        return super().undo()
