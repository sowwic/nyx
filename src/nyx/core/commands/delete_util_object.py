import logging
import typing
from collections import OrderedDict
from uuid import UUID

from PySide6 import QtGui

from ._base_nyx_command import NyxCommand
from ..exceptions import NyxCommandValidationError
from ..stage import Stage
from ..util_object import UtilObject
from ...static.enums import RestoreUuidOption

LOGGER = logging.getLogger(__name__)


class DeleteUtilObjectCommand(NyxCommand):
    """Delete util objects, restoring them from serialized data on undo."""

    def __init__(
        self,
        stage: Stage,
        util_objects: typing.Iterable[UtilObject | UUID],
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        """Initialize DeleteUtilObjectCommand.

        Args:
            stage (Stage): target stage.
            util_objects (typing.Iterable[UtilObject | UUID]): objects to delete.
            parent (QtGui.QUndoCommand | None): parent command.
        """
        super().__init__(stage=stage, text="Delete util objects", parent=parent)
        found = [
            self.stage.get_object(util_object, expected_type=UtilObject)
            for util_object in util_objects
        ]
        self.records: list[tuple[UUID, OrderedDict]] = [
            (util_object.node.uuid, util_object.serialize()) for util_object in found
        ]
        if len(found) == 1:
            self.setText(f"Delete {found[0].get_type_display_name().lower()}")

    def target_nodes(self):
        """list[Node]: nodes the command changes."""
        return [self.stage.get_object(node_uuid) for node_uuid, _ in self.records]

    def validate(self) -> None:
        """Check the objects exist and can be changed."""
        for _, data in self.records:
            util_object = self.stage.get_object(data[UtilObject.UUID_KEY])
            if util_object.is_locked:
                raise NyxCommandValidationError(f"{util_object.path} is locked")

    def redo(self) -> None:
        """Remove the objects from their nodes."""
        for node_uuid, data in self.records:
            util_object = self.stage.get_object(data[UtilObject.UUID_KEY])
            self.stage.get_object(node_uuid).remove_util_object(util_object)
        return super().redo()

    def undo(self) -> None:
        """Add the objects to their nodes again."""
        for node_uuid, data in self.records:
            UtilObject.deserialize(
                node=self.stage.get_object(node_uuid),
                serialized_data=data,
                restore_uuid=RestoreUuidOption.RESTORE,
            )
        return super().undo()
