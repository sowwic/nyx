import logging

from PySide6 import QtGui

from ..stage import Stage
from ..node_component import NodeComponent, NodeComponentLike
from ._base_nyx_command import NyxCommand


LOGGER = logging.getLogger(__name__)


class ReorderNodeComponentCommand(NyxCommand):
    def __init__(
        self,
        stage: Stage,
        node_component: NodeComponentLike,
        to_row: int,
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        super().__init__(stage=stage, text="Rename component", parent=parent)

        self.component_uuid = self.stage.get_object(
            node_component, expected_type=NodeComponent
        ).uuid
        self.from_row = None
        self.to_row = to_row

    def redo(self) -> None:
        component: NodeComponent = self.stage.get_object(self.component_uuid)
        self.from_row = component.row()
        component.model().move(self.from_row, self.to_row)
        self.setText(f"Reorder ({component.path} {self.from_row} -> {self.to_row})")

        return super().redo()

    def undo(self) -> None:
        component: NodeComponent = self.stage.get_object(self.component_uuid)
        component.model().move(self.to_row, self.from_row)

        return super().undo()
