import logging
import pathlib

from PySide6 import QtGui

from nyx.core import Node
from nyx.core import Stage
from nyx.core.exceptions import NyxCommandValidationError
from ._base_nyx_command import NyxCommand

LOGGER = logging.getLogger(__name__)


class SetNodeActiveStateCommand(NyxCommand):
    def __init__(
        self,
        stage: Stage,
        node: Node | pathlib.PurePosixPath | str | None,
        state: bool,
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        super().__init__(stage, "Set active state", parent)
        self.node_path = self.stage.pathify(node)
        self.old_state = None
        self.new_state = state
        self.setText(f"{self.text()} ({self.node_path} -> {self.new_state})")

    def redo(self) -> None:
        node = self.stage.node(self.node_path)
        self.old_state = node.is_active()
        node.set_active(self.new_state)
        return super().redo()

    def undo(self) -> None:
        node = self.stage.node(self.node_path)
        node.set_active(self.old_state)
        return super().undo()

    def validate(self):
        status = self.stage.node(self.node_path) is not None
        if not status:
            raise NyxCommandValidationError(f"Invalid node path: {self.node_path}")
