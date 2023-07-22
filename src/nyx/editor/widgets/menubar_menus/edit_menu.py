import typing
from PySide6 import QtGui
from PySide6 import QtWidgets

if typing.TYPE_CHECKING:
    from nyx.editor.main_window import NyxEditorMainWindow

from nyx.editor.widgets.menubar_menus._base_menu import BaseMenu


class EditMenu(BaseMenu):
    def __init__(self, main_window: "NyxEditorMainWindow", title: str = "&Edit", parent=None):
        super().__init__(main_window, title, parent)

    def create_actions(self):
        self.undo_action: QtWidgets.QAction = self.main_window.undo_group.createUndoAction(
            self)
        self.redo_action: QtWidgets.QAction = self.main_window.undo_group.createRedoAction(
            self)
        self.rename_selected_node_action = QtGui.QAction(
            'Rename selected node', self)

        self.undo_action.setShortcut("Ctrl+Z")
        self.redo_action.setShortcut("Ctrl+Y")
        self.rename_selected_node_action.setShortcut("F2")

    def create_connections(self):
        self.rename_selected_node_action.triggered.connect(
            self.on_rename_selected_node)

    def populate(self):
        self.addAction(self.undo_action)
        self.addAction(self.redo_action)
        self.addSeparator()
        self.addAction(self.rename_selected_node_action)

    def on_rename_selected_node(self):
        if not self.main_window.current_stage_graph:
            return
        self.main_window.current_stage_graph.gr_stage.start_selected_node_rename()
