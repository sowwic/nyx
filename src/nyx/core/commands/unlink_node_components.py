import typing
import logging
from collections.abc import Iterable
from uuid import UUID

from PySide6 import QtGui

from ._base_nyx_command import NyxCommand
from ..link import Link
from ..exceptions import NyxCommandValidationError, StageObjectQueryError

if typing.TYPE_CHECKING:
    from ..stage import Stage

LOGGER = logging.getLogger(__name__)


class UnlinkNodeComponentsCommand(NyxCommand):
    """Remove one or more links between components."""

    def __init__(
        self,
        stage: Stage,
        link_uuids: Iterable[UUID],
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        """Initialize UnlinkNodeComponentsCommand.

        Args:
            stage (Stage): target stage.
            link_uuids (Iterable[UUID]): uuids of the links to remove.
            parent (QtGui.QUndoCommand | None): parent command.
        """
        super().__init__(stage=stage, text="Unlink components", parent=parent)
        # Ordered and de-duplicated, so a link is never removed twice.
        self.link_uuids: list[UUID] = list(dict.fromkeys(link_uuids))
        # link uuid -> (source uuid, target uuid), filled when the links are removed
        self._ends: dict[UUID, tuple[UUID, UUID]] = {}

    def redo(self) -> None:
        """Remove the links."""
        links: list[Link] = [self.stage.get_object(uuid) for uuid in self.link_uuids]
        self._ends = {link.uuid: (link.source, link.target) for link in links}

        if len(links) == 1:
            self.setText(f"Unlink components: {links[0].path_connection_str}")
        else:
            self.setText(f"Unlink {len(links)} components")
        for link in links:
            self.stage.unregister_link(link)

        return super().redo()

    def undo(self) -> None:
        """Recreate the links with their original uuids."""
        for link_uuid in reversed(self.link_uuids):
            source_uuid, target_uuid = self._ends[link_uuid]
            self.stage.link_components(
                source_component=source_uuid,
                target_component=target_uuid,
                use_uuid=link_uuid,
            )
        return super().undo()

    def validate(self):
        """Check there is something to remove and all the links exist."""
        if not self.link_uuids:
            raise NyxCommandValidationError("No links provided for unlink")
        for link_uuid in self.link_uuids:
            try:
                self.stage.get_object(link_uuid)
            except StageObjectQueryError:
                raise NyxCommandValidationError(
                    f"Invalid link provided for unlink: {link_uuid}"
                )
