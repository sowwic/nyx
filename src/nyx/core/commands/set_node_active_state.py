import logging

from PySide6 import QtGui
from ._base_nyx_command import NyxCommand
from ..node import Node, NodeLike
from ..stage import Stage
from ..exceptions import NyxCommandValidationError, StageObjectQueryError

LOGGER = logging.getLogger(__name__)


class SetNodeActiveStateCommand(NyxCommand):
    """Set the active state of a node."""

    def __init__(
        self,
        stage: Stage,
        node: NodeLike,
        state: bool,
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        """Initialize SetNodeActiveStateCommand.

        Args:
            stage (Stage): target stage.
            node (NodeLike): node to change.
            state (bool): new active state.
            parent (QtGui.QUndoCommand | None): parent command.
        """
        super().__init__(stage, "Set active state", parent)
        self.node_path = self.stage.pathify(node)
        self.old_state = None
        self.new_state = state
        self.setText(f"{self.text()} ({self.node_path} -> {self.new_state})")

    def redo(self) -> None:
        """Apply the new active state."""
        node = self.stage.get_object(self.node_path, expected_type=Node)
        self.old_state = node.is_active()
        node.set_active(self.new_state)
        return super().redo()

    def undo(self) -> None:
        """Restore the previous active state."""
        node = self.stage.get_object(self.node_path)
        node.set_active(self.old_state)
        return super().undo()

    def validate(self):
        """Check the node exists."""
        try:
            self.stage.get_object(self.node_path)
        except StageObjectQueryError:
            raise NyxCommandValidationError(f"Invalid node path: {self.node_path}")
