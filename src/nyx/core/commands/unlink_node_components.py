import typing
import logging
from uuid import UUID

from PySide6 import QtGui

from ._base_nyx_command import NyxCommand
from ..link import Link
from ..exceptions import NyxCommandValidationError, StageObjectQueryError

if typing.TYPE_CHECKING:
    from ..stage import Stage

LOGGER = logging.getLogger(__name__)


class UnlinkNodeComponentsCommand(NyxCommand):
    def __init__(
        self,
        stage: Stage,
        link_uuid: UUID,
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        super().__init__(stage=stage, text="Unlink components", parent=parent)
        self.link_uuid = link_uuid
        self.source_uuid = None
        self.target_uuid = None

    def redo(self) -> None:
        link: Link = self.stage.get_object(self.link_uuid)

        self.source_uuid = link.source
        self.target_uuid = link.target

        self.setText(f"Unlink components: {link.path_connection_str}")
        self.stage.unregister_link(link)

        return super().redo()

    def undo(self) -> None:
        self.stage.link_components(
            source_component=self.source_uuid,
            target_component=self.target_uuid,
            use_uuid=self.link_uuid,
        )
        return super().undo()

    def validate(self):
        try:
            self.stage.get_object(self.link_uuid)
        except StageObjectQueryError:
            raise NyxCommandValidationError(
                f"Invalid link provided for unlink: {self.link_uuid}"
            )
