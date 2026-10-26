import logging

from PySide6 import QtGui
from ._base_nyx_command import NyxCommand
from ..node_component import NodeComponent, NodeComponentLike
from ..stage import Stage
from ...static.enums import NodeComponentFlag

LOGGER = logging.getLogger(__name__)


class SetNodeComponentFlagCommand(NyxCommand):
    """Set or clear a flag of a component."""

    MODIFIES_STRUCTURE = True

    def __init__(
        self,
        stage: Stage,
        node_component: NodeComponentLike,
        flag: NodeComponentFlag,
        role: NodeComponent.Roles,
        state: bool,
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        """Initialize SetNodeComponentFlagCommand.

        Args:
            stage (Stage): target stage.
            node_component (NodeComponentLike): component to change.
            flag (NodeComponentFlag): flag to change.
            role (NodeComponent.Roles): role the flag is set for.
            state (bool): whether the flag is set.
            parent (QtGui.QUndoCommand | None): parent command.
        """
        super().__init__(stage, "", parent)
        component = self.stage.get_object(node_component, expected_type=NodeComponent)
        self.component_uuid = component.uuid
        self.flag = flag
        self.role = role
        self.old_state = None
        self.new_state = state
        self.setText(f"Set {flag.name} ({component.path} -> {self.new_state})")

    @property
    def component(self) -> NodeComponent:
        """NodeComponent: component the command operates on."""
        return self.stage.get_object(self.component_uuid, expected_type=NodeComponent)

    def target_nodes(self):
        """list[Node]: nodes the command changes."""
        return [self.stage.get_object(self.component_uuid).node]

    def redo(self) -> None:
        """Apply the new flag state."""
        component = self.component

        self.old_state = self.flag in component.component_flags
        component.set_component_flag(self.flag, self.role, state=self.new_state)
        return super().redo()

    def undo(self) -> None:
        """Restore the previous flag state."""
        self.component.set_component_flag(self.flag, self.role, self.old_state)
        return super().undo()
