import logging

from PySide6 import QtGui
from ._base_nyx_command import NyxCommand
from ..node_component import NodeComponent, NodeComponentLike
from ..stage import Stage

LOGGER = logging.getLogger(__name__)


class SetNodeComponentActiveStateCommand(NyxCommand):
    def __init__(
        self,
        stage: Stage,
        node_component: NodeComponentLike,
        state: bool,
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        super().__init__(stage, "Set active state", parent)
        component = self.stage.get_object(node_component, expected_type=NodeComponent)
        self.component_uuid = component.uuid
        self.old_state = None
        self.new_state = state
        self.setText(f"{self.text()} ({component.path} -> {self.new_state})")

    @property
    def component(self) -> NodeComponent:
        return self.stage.get_object(self.component_uuid, expected_type=NodeComponent)

    def redo(self) -> None:
        component = self.component
        self.old_state = component.is_active
        component.is_active = self.new_state
        return super().redo()

    def undo(self) -> None:
        self.component.is_active = self.old_state
        return super().undo()
