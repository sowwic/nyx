import typing
from PySide6 import QtWidgets

if typing.TYPE_CHECKING:
    from nyx.editor.main_window import NyxEditorMainWindow


class BaseMenu(QtWidgets.QMenu):

    def __init__(self, main_window: "NyxEditorMainWindow", title: str = "Menu", parent=None):
        super(BaseMenu, self).__init__(title, parent)
        self._main_window = main_window

        self.setTearOffEnabled(True)
        self.create_actions()
        self.populate()
        self.create_connections()

    @property
    def main_window(self):
        return self._main_window

    @property
    def current_stage_graph(self):
        return self.main_window.current_stage_graph

    def create_actions(self):
        pass

    def populate(self):
        pass

    def create_connections(self):
        pass
