import logging
import pathlib

from PySide6 import QtGui

from ..stage import Stage
from ..node import NodeLike
from nyx.core.exceptions import NyxCommandValidationError, StageObjectQueryError
from ._base_nyx_command import NyxCommand
from ..name_validator import NameValidator


LOGGER = logging.getLogger(__name__)


class RenameNodeCommand(NyxCommand):
    """Rename a node."""

    def __init__(
        self,
        stage: Stage,
        node: NodeLike,
        new_name: str,
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        """Initialize RenameNodeCommand.

        Args:
            stage (Stage): target stage.
            node (NodeLike): node to rename.
            new_name (str): new name, sanitized to a valid object name.
            parent (QtGui.QUndoCommand | None): parent command.
        """
        super().__init__(stage=stage, text="Rename node", parent=parent)

        self.path_to_rename = self.stage.pathify(node)
        self.new_name = NameValidator.get_valid_stage_object_name(new_name)
        self.old_name: str = None

        self.node_data: dict = None
        self.renamed_node_data: pathlib.PurePosixPath = None

    def redo(self) -> None:
        """Rename the node."""
        node = self.stage.get_object(self.path_to_rename)
        self.old_name = node.name
        self.node_data = node.serialize()
        self.setText(f"Rename node ({node.path.as_posix()} -> {self.new_name})")

        # node = self.stage.get_object(self.node_data.get("path"))
        node.rename(self.new_name)
        self.renamed_node_data = node.serialize()
        return super().redo()

    def undo(self) -> None:
        """Restore the previous node name."""
        node = self.stage.get_object(self.renamed_node_data.get("uuid"))
        node.rename(self.old_name)
        return super().undo()

    def validate(self):
        """Check the node exists."""
        try:
            self.stage.get_object(self.path_to_rename)
        except StageObjectQueryError:
            raise NyxCommandValidationError(
                f"Invalid node for renaming: {self.path_to_rename}"
            )
