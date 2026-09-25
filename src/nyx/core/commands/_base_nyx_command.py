import logging

from PySide6 import QtGui
from nyx.core import Stage

LOGGER = logging.getLogger(__name__)


class NyxCommand(QtGui.QUndoCommand):
    def __init__(
        self, stage: Stage, text: str, parent: QtGui.QUndoCommand | None = None
    ) -> None:
        super().__init__(text, parent=parent)
        self.stage = stage

    def validate(self) -> None: ...
