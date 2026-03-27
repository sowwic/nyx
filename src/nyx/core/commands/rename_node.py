import logging
import pathlib

from PySide6 import QtGui

from nyx.core import Node
from nyx.core import Stage
from nyx.core.exceptions import NyxCommandValidationError
from ._base_nyx_command import NyxCommand


LOGGER = logging.getLogger(__name__)


class RenameNodeCommand(NyxCommand):
    def __init__(
        self,
        stage: Stage,
        node: Node | pathlib.PurePosixPath | str,
        new_name: str,
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        super().__init__(stage=stage, text="Rename node", parent=parent)

        self.path_to_rename = self.stage.pathify(node)
        self.new_name = new_name
        self.old_name: str = None

        self.node_data: dict = None
        self.renamed_node_data: pathlib.PurePosixPath = None

    def redo(self) -> None:
        node = self.stage.node(self.path_to_rename)
        self.old_name = node.name
        self.node_data = node.serialize()
        self.setText(f"Rename node ({node.path.as_posix()} -> {self.new_name})")

        # node = self.stage.node(self.node_data.get("path"))
        node.rename(self.new_name)
        self.renamed_node_data = node.serialize()
        return super().redo()

    def undo(self) -> None:
        node = self.stage.node(self.renamed_node_data.get("path"))
        node.rename(self.old_name)
        return super().undo()

    def validate(self):
        status = self.stage.node(self.path_to_rename) is not None
        if not status:
            raise NyxCommandValidationError(
                f"Invalid node for renaming: {self.path_to_rename}"
            )
