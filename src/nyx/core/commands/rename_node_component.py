import logging

from PySide6 import QtGui

from ..stage import Stage
from ..node_component import NodeComponent, NodeComponentLike
from nyx.core.exceptions import NyxCommandValidationError
from ._base_nyx_command import NyxCommand
from ..name_validator import NameValidator


LOGGER = logging.getLogger(__name__)


class RenameNodeComponentCommand(NyxCommand):
    """Rename a node component, keeping the name unique within its node."""

    MODIFIES_STRUCTURE = True

    def __init__(
        self,
        stage: Stage,
        node_component: NodeComponentLike,
        new_name: str,
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        """Initialize RenameNodeComponentCommand.

        Args:
            stage (Stage): target stage.
            node_component (NodeComponentLike): component to rename.
            new_name (str): new display name, the address name is made from it.
            parent (QtGui.QUndoCommand | None): parent command.
        """
        super().__init__(stage=stage, text="Rename component", parent=parent)

        self.path_to_rename = self.stage.pathify(node_component)
        self.component_uuid = None
        self.new_name = new_name.strip()
        self.old_name: str = None
        self.old_display_name: str = None

    def target_nodes(self):
        """list[Node]: nodes the command changes."""
        return [self.stage.get_object(self.path_to_rename).node]

    def redo(self) -> None:
        """Rename the component."""
        node_component: NodeComponent = self.stage.get_object(self.path_to_rename)
        self.component_uuid = node_component.uuid
        self.old_name = node_component.name
        self.old_display_name = node_component.data(NodeComponent.Roles.DISPLAY_NAME)
        self.setText(f"Rename component ({node_component.path} -> {self.new_name})")

        node_component.rename_display(self.new_name)
        return super().redo()

    def undo(self) -> None:
        """Restore the previous component name."""
        component: NodeComponent = self.stage.get_object(self.component_uuid)
        component.name = self.old_name
        component.display_name = self.old_display_name or ""
        component.emitDataChanged()
        return super().undo()

    def validate(self):
        """Check the component exists and the new name can make an address name."""
        if not NameValidator.to_address_name(self.new_name):
            raise NyxCommandValidationError(
                f"Invalid component name, it needs a letter or a digit: "
                f"{self.new_name!r}"
            )
        status = self.stage.get_object(self.path_to_rename) is not None
        if not status:
            raise NyxCommandValidationError(
                f"Invalid component for renaming: {self.path_to_rename}"
            )
