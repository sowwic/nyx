import typing
from PySide2 import QtWidgets

if typing.TYPE_CHECKING:
    from nyx.editor.main_window import NyxEditorMainWindow


class EditorToolBar(QtWidgets.QToolBar):
    def __init__(self, main_window: "NyxEditorMainWindow", parent: QtWidgets.QWidget = None) -> None:
        super().__init__("Tools", parent)
        self.main_window: "NyxEditorMainWindow" = main_window
