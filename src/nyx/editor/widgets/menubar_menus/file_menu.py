import typing
# from PySide2 import QtWidgets

if typing.TYPE_CHECKING:
    from nyx.editor.main_window import NyxEditorMainWindow

from nyx.editor.widgets.menubar_menus._base_menu import BaseMenu


class FileMenu(BaseMenu):
    def __init__(self, main_window: "NyxEditorMainWindow", title: str = "&File", parent=None):
        super().__init__(main_window, title, parent)

    def create_actions(self):
        pass

    def populate(self):
        pass
