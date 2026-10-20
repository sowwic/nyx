import logging

from PySide6 import QtGui

from ._base_nyx_command import NyxCommand
from ..node_component import NodeComponent, NodeComponentLike
from ..stage import Stage

LOGGER = logging.getLogger(__name__)


class SetNodeComponentDatatypeCommand(NyxCommand):
    """Set the datatype hint of a component."""

    def __init__(
        self,
        stage: Stage,
        node_component: NodeComponentLike,
        datatype_id: str,
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        """Initialize SetNodeComponentDatatypeCommand.

        Args:
            stage (Stage): target stage.
            node_component (NodeComponentLike): component to change.
            datatype_id (str): type id of the new datatype.
            parent (QtGui.QUndoCommand | None): parent command.
        """
        super().__init__(stage, "Set datatype", parent)
        component = self.stage.get_object(node_component, expected_type=NodeComponent)
        self.component_uuid = component.uuid
        self.old_datatype_id = component.datatype_id
        self.new_datatype_id = str(datatype_id)
        self.setText(f"{self.text()} ({component.path} -> {self.new_datatype_id})")

    @property
    def component(self) -> NodeComponent:
        """NodeComponent: component the command operates on."""
        return self.stage.get_object(self.component_uuid, expected_type=NodeComponent)

    def redo(self) -> None:
        """Apply the new datatype."""
        self.component.set_datatype(self.new_datatype_id)
        return super().redo()

    def undo(self) -> None:
        """Restore the previous datatype."""
        self.component.set_datatype(self.old_datatype_id)
        return super().undo()
