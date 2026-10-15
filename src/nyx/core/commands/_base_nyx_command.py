import logging
import weakref

from PySide6 import QtGui
from nyx.core import Stage

LOGGER = logging.getLogger(__name__)


class NyxCommand(QtGui.QUndoCommand):
    def __init__(
        self, stage: Stage, text: str, parent: QtGui.QUndoCommand | None = None
    ) -> None:
        super().__init__(text, parent=parent)
        # Weak: the stage owns the undo stack that owns this command, so a strong
        # reference forms a cycle that cannot be torn down safely by the GC.
        self._stage_ref = weakref.ref(stage)

    @property
    def stage(self) -> Stage:
        return self._stage_ref()

    def validate(self) -> None: ...
