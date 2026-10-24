import logging
import typing
import weakref

from PySide6 import QtGui
from nyx.core import Stage
from nyx.core.exceptions import NyxCommandValidationError

if typing.TYPE_CHECKING:
    from nyx.core.node import Node

LOGGER = logging.getLogger(__name__)


class NyxCommand(QtGui.QUndoCommand):
    """Base undo command bound to a stage.

    The stage is held weakly because it owns the undo stack that owns this command.

    Commands change nodes of the stage: they list them in `target_nodes`, so the stage
    can refuse to change nodes that belong to a reference node.

    Attributes:
        MODIFIES_STRUCTURE: the command adds, removes or redefines components or
            nodes, which the nodes may not allow.
    """

    MODIFIES_STRUCTURE: bool = False

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

    def target_nodes(self) -> typing.Iterable[Node | None]:
        """Get the nodes the command changes.

        Returns:
            Iterable[Node | None]: nodes changed by the command. Override in
                subclasses.
        """
        return ()

    def validate_not_locked(self) -> None:
        """Check the nodes the command changes can be changed.

        Raises:
            NyxCommandValidationError: if a node belongs to a reference node, or the
                command changes the structure of a node that doesn't allow it.
        """
        for node in self.target_nodes():
            if node is None:
                continue
            if node.is_in_locked_scope:
                raise NyxCommandValidationError(
                    f"{node.path} belongs to a reference and can't be changed"
                )
            if self.MODIFIES_STRUCTURE and not node.ALLOWS_STRUCTURE_CHANGES:
                raise NyxCommandValidationError(
                    f"The structure of {node.path} can't be changed"
                )
