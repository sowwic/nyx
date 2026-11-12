import typing

from PySide6 import QtCore, QtWidgets

from nyx.editor.core.action_registry import ACTION_REGISTRY
from nyx.editor.core.actions import ActionId

if typing.TYPE_CHECKING:
    from nyx.editor.main_window import NyxEditorMainWindow


class EditorToolBar(QtWidgets.QToolBar):
    """Toolbar with the node and execution actions."""

    def __init__(
        self, main_window: NyxEditorMainWindow, parent: QtWidgets.QWidget = None
    ) -> None:
        """Initialize EditorToolBar.

        Args:
            main_window (NyxEditorMainWindow): editor main window.
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__("Tools", parent)
        self.main_window: NyxEditorMainWindow = main_window
        self.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        for action_id in (
            ActionId.CREATE_NODE,
            ActionId.DELETE_NODE,
            ActionId.EXECUTE_STAGE,
            ActionId.EXECUTE_FROM_SELECTED,
        ):
            self.addAction(ACTION_REGISTRY.action(action_id))
