import typing
# from PySide2 import QtWidgets

if typing.TYPE_CHECKING:
    from nyx.editor.main_window import NyxEditorMainWindow

from nyx.editor.widgets.menubar_menus._base_menu import BaseMenu


class WindowMenu(BaseMenu):
    def __init__(self, main_window: "NyxEditorMainWindow", title: str = "&Window", parent=None):
        super().__init__(main_window, title, parent)

    def populate(self):
        self.addAction(self.main_window.stage_tree_dock.toggleViewAction())
        self.addAction(self.main_window.undo_dock.toggleViewAction())
