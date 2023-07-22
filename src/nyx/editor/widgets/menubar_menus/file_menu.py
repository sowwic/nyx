import typing
from PySide6 import QtGui
from PySide6 import QtWidgets

if typing.TYPE_CHECKING:
    from nyx.editor.main_window import NyxEditorMainWindow

from nyx.editor.widgets.menubar_menus._base_menu import BaseMenu


class FileMenu(BaseMenu):
    def __init__(self, main_window: "NyxEditorMainWindow", title: str = "&File", parent=None):
        super().__init__(main_window, title, parent)

    def create_actions(self):
        self.new_stage_action = QtGui.QAction("New Stage", self)
        self.open_stage_action = QtGui.QAction("Open Stage", self)
        self.open_stage_as_new_tab_action = QtGui.QAction(
            "Open Stage As New Tab", self)
        self.save_stage_action = QtGui.QAction("Save Stage", self)
        self.save_stage_as_action = QtGui.QAction("Save Stage As...", self)

        self.new_stage_action.setShortcut("Ctrl+Shift+N")
        self.open_stage_action.setShortcut("Ctrl+Shift+O")
        self.save_stage_action.setShortcut("Ctrl+Shift+S")

    def populate(self):
        self.addAction(self.new_stage_action)
        self.addAction(self.open_stage_action)
        self.addAction(self.open_stage_as_new_tab_action)
        self.addAction(self.save_stage_action)
        self.addAction(self.save_stage_as_action)

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
