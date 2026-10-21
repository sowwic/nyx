import logging

from PySide6 import QtGui

from ._base_nyx_command import NyxCommand
from ..exceptions import NyxCommandValidationError
from ..node_component import NodeComponent, NodeComponentLike
from ..stage import Stage
from ...static.enums import NoteFormat

LOGGER = logging.getLogger(__name__)


class SetNodeComponentNoteCommand(NyxCommand):
    """Set the note of a component, and how it is written."""

    def __init__(
        self,
        stage: Stage,
        node_component: NodeComponentLike,
        text: str,
        note_format: NoteFormat | str | None = None,
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        """Initialize SetNodeComponentNoteCommand.

        Args:
            stage (Stage): target stage.
            node_component (NodeComponentLike): component to change.
            text (str): new note, empty to remove it.
            note_format (NoteFormat | str | None): format of the new note. The one
                the component has is kept if omitted.
            parent (QtGui.QUndoCommand | None): parent command.
        """
        super().__init__(stage, "Set note", parent)
        component = self.stage.get_object(node_component, expected_type=NodeComponent)
        self.component_uuid = component.uuid
        self.new_text = text
        self.new_format = (
            component.note_format if note_format is None else str(note_format)
        )
        self.old_text = component.note
        self.old_format = component.note_format
        self.setText(f"{self.text()} ({component.path})")

    @property
    def component(self) -> NodeComponent:
        """NodeComponent: component the command operates on."""
        return self.stage.get_object(self.component_uuid, expected_type=NodeComponent)

    def validate(self) -> None:
        """Check the format is one that exists."""
        try:
            NoteFormat(self.new_format)
        except ValueError as err:
            raise NyxCommandValidationError(
                f"Unknown note format: {self.new_format}"
            ) from err

    def redo(self) -> None:
        """Set the new note."""
        component = self.component
        component.note_format = self.new_format
        component.note = self.new_text
        return super().redo()

    def undo(self) -> None:
        """Set the previous note back."""
        component = self.component
        component.note_format = self.old_format
        component.note = self.old_text
        return super().undo()
