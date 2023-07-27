import typing
from PySide2 import QtWidgets

if typing.TYPE_CHECKING:
    from nyx.editor.main_window import NyxEditorMainWindow

from nyx.editor.widgets.menubar_menus._base_menu import BaseMenu
from nyx.editor.utils.io import (
    export_selected_nodes, import_nodes_from_explorer)


class FileMenu(BaseMenu):
    def __init__(self, main_window: "NyxEditorMainWindow", title: str = "&File", parent=None):
        super().__init__(main_window, title, parent)

    def create_actions(self):
        self.new_stage_action = QtWidgets.QAction("New Stage", self)
        self.open_stage_action = QtWidgets.QAction("Open Stage", self)
        self.open_stage_as_new_tab_action = QtWidgets.QAction(
            "Open Stage As New Tab", self)
        self.save_stage_action = QtWidgets.QAction("Save Stage", self)
        self.save_stage_as_action = QtWidgets.QAction("Save Stage As...", self)
        self.export_selected_nodes_action = QtWidgets.QAction(
            "Export Selected Nodes As...", self)
        self.import_nodes_from_file_action = QtWidgets.QAction(
            "Import Nodes", self)
        self.reference_nodes_from_file_action = QtWidgets.QAction(
            "Reference Nodes", self)

        self.new_stage_action.setShortcut("Ctrl+Shift+N")
        self.open_stage_action.setShortcut("Ctrl+Shift+O")
        self.save_stage_action.setShortcut("Ctrl+Shift+S")

    def populate(self):
        self.addAction(self.new_stage_action)
        self.addAction(self.open_stage_action)
        self.addAction(self.open_stage_as_new_tab_action)
        self.addAction(self.save_stage_action)
        self.addAction(self.save_stage_as_action)
        self.addSection("Nodes")
        self.addAction(self.import_nodes_from_file_action)
        self.addAction(self.reference_nodes_from_file_action)
        self.addAction(self.export_selected_nodes_action)

    def create_connections(self):
        self.new_stage_action.triggered.connect(self.main_window.on_stage_new)
        self.open_stage_action.triggered.connect(
            self.main_window.on_stage_open)
        self.open_stage_as_new_tab_action.triggered.connect(
            self.main_window.on_stage_open_tabbed)
        self.save_stage_action.triggered.connect(
            self.main_window.on_stage_save)
        self.save_stage_as_action.triggered.connect(
            self.main_window.on_stage_save_as)
        self.export_selected_nodes_action.triggered.connect(
            export_selected_nodes)
        self.import_nodes_from_file_action.triggered.connect(
            import_nodes_from_explorer)
        self.reference_nodes_from_file_action.triggered.connect(
            lambda: import_nodes_from_explorer(as_reference=True))
