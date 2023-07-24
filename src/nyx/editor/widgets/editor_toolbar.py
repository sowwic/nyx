import typing
from PySide2 import QtCore
from PySide2 import QtWidgets

if typing.TYPE_CHECKING:
    from nyx.editor.main_window import NyxEditorMainWindow


class EditorToolBar(QtWidgets.QToolBar):
    def __init__(self, main_window: "NyxEditorMainWindow", parent: QtWidgets.QWidget = None) -> None:
        super().__init__("Tools", parent)
        self.main_window: "NyxEditorMainWindow" = main_window
        self.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.addAction(self.main_window.stage_tree_view.create_new_node_action)
        self.addAction(
            self.main_window.stage_tree_view.delete_selected_node_action)
        self.addAction(self.main_window.execute_stage_action)
        self.addAction(self.main_window.execute_from_selected_node_action)
