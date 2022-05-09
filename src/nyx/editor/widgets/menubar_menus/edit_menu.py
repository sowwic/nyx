import typing
from PySide2 import QtWidgets

if typing.TYPE_CHECKING:
    from nyx.editor.main_window import NyxEditorMainWindow

from nyx.editor.widgets.menubar_menus._base_menu import BaseMenu


class EditMenu(BaseMenu):
    def __init__(self, main_window: "NyxEditorMainWindow", title: str = "&Edit", parent=None):
        super().__init__(main_window, title, parent)

    def create_actions(self):
        self.undo_action: QtWidgets.QAction = self.main_window.undo_group.createUndoAction(self)
        self.redo_action: QtWidgets.QAction = self.main_window.undo_group.createRedoAction(self)

        self.undo_action.setShortcut("Ctrl+Z")
        self.redo_action.setShortcut("Ctrl+Y")

    def populate(self):
        self.addAction(self.undo_action)
        self.addAction(self.redo_action)
