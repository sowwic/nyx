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
            new_name (str): new display name, the address name is made from it.
            parent (QtGui.QUndoCommand | None): parent command.
        """
        super().__init__(stage=stage, text="Rename node", parent=parent)

        self.path_to_rename = self.stage.pathify(node)
        self.new_name = new_name.strip()
        self.old_name: str = None
        self.old_display_name: str = None

        self.node_data: dict = None
        self.renamed_node_data: pathlib.PurePosixPath = None

    def target_nodes(self):
        """list[Node]: nodes the command changes."""
        return [self.stage.get_object(self.path_to_rename)]

    def redo(self) -> None:
        """Rename the node."""
        node = self.stage.get_object(self.path_to_rename)
        self.old_name = node.name
        self.old_display_name = node.display_name
        self.node_data = node.serialize()
        self.setText(f"Rename node ({node.path.as_posix()} -> {self.new_name})")

        node.rename_display(self.new_name)
        self.renamed_node_data = node.serialize()
        return super().redo()

    def undo(self) -> None:
        """Restore the previous node name."""
        node = self.stage.get_object(self.renamed_node_data.get("uuid"))
        node.rename(self.old_name)
        node.set_display_name(self.old_display_name)
        return super().undo()

    def validate(self):
        """Check the node exists and the new name can make an address name."""
        if not NameValidator.to_address_name(self.new_name):
            raise NyxCommandValidationError(
                f"Invalid node name, it needs a letter or a digit: {self.new_name!r}"
            )
        try:
            self.stage.get_object(self.path_to_rename)
        except StageObjectQueryError:
            raise NyxCommandValidationError(
                f"Invalid node for renaming: {self.path_to_rename}"
            )
