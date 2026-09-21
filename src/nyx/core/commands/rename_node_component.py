import logging
import pathlib

from PySide6 import QtGui

from ..stage import Stage
from ..node_component import NodeComponent
from nyx.core.exceptions import NyxCommandValidationError
from ._base_nyx_command import NyxCommand
from ..name_validator import NameValidator


LOGGER = logging.getLogger(__name__)


class RenameNodeComponentCommand(NyxCommand):
    def __init__(
        self,
        stage: Stage,
        node_component: NodeComponent | pathlib.PurePosixPath | str,
        new_name: str,
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        super().__init__(stage=stage, text="Rename component", parent=parent)

        self.path_to_rename = self.stage.pathify(node_component)
        self.renamed_path = None
        self.new_name = NameValidator.get_valid_stage_object_name(new_name)
        self.old_name: str = None

    def redo(self) -> None:
        node_component: NodeComponent = self.stage.node_component(self.path_to_rename)
        self.old_name = node_component.name
        self.setText(f"Rename component ({node_component.as_path()} -> {self.new_name})")

        node_component.name = self.new_name
        self.renamed_path = node_component.as_path()
        return super().redo()

    def undo(self) -> None:
        component: NodeComponent = self.stage.node_component(self.renamed_path)
        component.name = self.old_name
        return super().undo()

    def validate(self):
        status = self.stage.node_component(self.path_to_rename) is not None
        if not status:
            raise NyxCommandValidationError(
                f"Invalid component for renaming: {self.path_to_rename}"
            )
