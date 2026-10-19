import logging
import weakref

from PySide6 import QtGui
from nyx.core import Stage

LOGGER = logging.getLogger(__name__)


class NyxCommand(QtGui.QUndoCommand):
    """Base undo command bound to a stage.

    The stage is held weakly because it owns the undo stack that owns this command.
    """

    def __init__(
        self, stage: Stage, text: str, parent: QtGui.QUndoCommand | None = None
    ) -> None:
        """Initialize NyxCommand.

        Args:
            stage (Stage): stage the command operates on.
            text (str): undo stack text.
            parent (QtGui.QUndoCommand | None): parent command.
        """
        super().__init__(text, parent=parent)
        # Weak: the stage owns the undo stack that owns this command, so a strong
        # reference forms a cycle that cannot be torn down safely by the GC.
        self._stage_ref = weakref.ref(stage)

    @property
    def stage(self) -> Stage:
        """Stage: stage the command operates on."""
        return self._stage_ref()

    def validate(self) -> None:
        """Check the command can be executed.

        Raises:
            NyxCommandValidationError: if the command arguments are invalid.
        """
