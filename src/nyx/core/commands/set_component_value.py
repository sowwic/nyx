import logging
import typing

from PySide6 import QtGui
from ._base_nyx_command import NyxCommand
from ..node_component import NodeComponent, NodeComponentLike
from ..stage import Stage

LOGGER = logging.getLogger(__name__)


class SetNodeComponentValueCommand(NyxCommand):
    def __init__(
        self,
        stage: Stage,
        node_component: NodeComponentLike,
        value: typing.Any,
        raw: bool = False,
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        super().__init__(stage, "Set value", parent)
        component = self.stage.get_object(node_component, expected_type=NodeComponent)
        self.component_uuid = component.uuid
        self.raw = raw
        self.old_value = None
        self.new_value = value
        self.setText(f"{self.text()} ({component.path} -> {self.new_value})")

    @property
    def component(self) -> NodeComponent:
        return self.stage.get_object(self.component_uuid, expected_type=NodeComponent)

    def redo(self) -> None:
        component = self.component
        self.old_value = component.value
        new_value = self.new_value
        if isinstance(self.new_value, str) and not self.raw:
            try:
                new_value = eval(self.new_value)
            except Exception:
                LOGGER.warning(f"Failed to eval {self.new_value}, defaulting to str")

        component.value = new_value
        return super().redo()

    def undo(self) -> None:
        self.component.value = self.old_value
        return super().undo()
