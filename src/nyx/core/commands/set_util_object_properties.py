import typing
from uuid import UUID

from PySide6 import QtGui

from ._base_nyx_command import NyxCommand
from ..exceptions import NyxCommandValidationError
from ..stage import Stage
from ..util_object import UtilObject


class SetUtilObjectPropertiesCommand(NyxCommand):
    """Change properties of util objects: move, resize, edit the text, ...."""

    def __init__(
        self,
        stage: Stage,
        changes: typing.Mapping[UtilObject | UUID, typing.Mapping[str, typing.Any]],
        text: str = "Edit util objects",
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        """Initialize SetUtilObjectPropertiesCommand.

        Args:
            stage (Stage): target stage.
            changes (typing.Mapping): new properties by util object, as listed by
                `UtilObject.serialize_properties`.
            text (str): undo stack text.
            parent (QtGui.QUndoCommand | None): parent command.
        """
        super().__init__(stage=stage, text=text, parent=parent)
        self.new_properties: dict[UUID, dict[str, typing.Any]] = {}
        self.old_properties: dict[UUID, dict[str, typing.Any]] = {}
        for util_object, properties in changes.items():
            util_object = self.stage.get_object(util_object, expected_type=UtilObject)
            current = util_object.serialize_properties()
            self.new_properties[util_object.uuid] = dict(properties)
            self.old_properties[util_object.uuid] = {
                name: current[name] for name in properties if name in current
            }

    def target_nodes(self):
        """list[Node]: nodes the command changes."""
        return [self.stage.get_object(uuid).node for uuid in self.new_properties]

    def validate(self) -> None:
        """Check the objects can be changed."""
        for uuid in self.new_properties:
            util_object = self.stage.get_object(uuid)
            if util_object.is_locked:
                raise NyxCommandValidationError(f"{util_object.path} is locked")

    def redo(self) -> None:
        """Set the new properties."""
        self._apply(self.new_properties)
        return super().redo()

    def undo(self) -> None:
        """Set the old properties back."""
        self._apply(self.old_properties)
        return super().undo()

    def _apply(self, properties_by_uuid: dict[UUID, dict[str, typing.Any]]) -> None:
        for uuid, properties in properties_by_uuid.items():
            self.stage.get_object(uuid, expected_type=UtilObject).apply_properties(
                properties
            )
