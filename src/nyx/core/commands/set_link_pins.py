import logging

from PySide6 import QtCore, QtGui

from ._base_nyx_command import NyxCommand
from ..link import Link, LinkLike
from ..stage import Stage

LOGGER = logging.getLogger(__name__)


class SetLinkPinsCommand(NyxCommand):
    """Set the pins of a link: add, move or remove them."""

    def __init__(
        self,
        stage: Stage,
        link: LinkLike,
        pins: list[QtCore.QPointF],
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        """Initialize SetLinkPinsCommand.

        Args:
            stage (Stage): target stage.
            link (LinkLike): link to change.
            pins (list[QtCore.QPointF]): new pins, from the source to the target.
            parent (QtGui.QUndoCommand | None): parent command.
        """
        super().__init__(stage, "Set link pins", parent)
        link = self.stage.get_object(link, expected_type=Link)
        self.link_uuid = link.uuid
        self.old_pins = link.pins
        self.new_pins = [QtCore.QPointF(pin) for pin in pins]
        self.setText(f"{self.text()} ({link.path_connection_str})")

    @property
    def link(self) -> Link:
        """Link: link the command operates on."""
        return self.stage.get_object(self.link_uuid, expected_type=Link)

    def target_nodes(self):
        """list[Node]: nodes the command changes, the ones the link connects."""
        link = self.link
        return [link.source_node, link.target_node]

    def redo(self) -> None:
        """Set the new pins."""
        self.link.pins = self.new_pins
        return super().redo()

    def undo(self) -> None:
        """Set the previous pins back."""
        self.link.pins = self.old_pins
        return super().undo()
