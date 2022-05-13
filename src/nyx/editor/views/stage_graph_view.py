import typing
# import pathlib
# from PySide2 import QtCore
# from PySide2 import QtGui
from PySide2 import QtWidgets

from nyx import get_main_logger

if typing.TYPE_CHECKING:
    from nyx.editor.widgets.stage_graph_editor import StageGraphEditor


LOGGER = get_main_logger()


class StageGraphView(QtWidgets.QGraphicsView):

    def __init__(self, graph_editor: "StageGraphEditor", parent: QtWidgets.QWidget = None) -> None:

        super().__init__(graph_editor.gr_scene, parent=parent)
        self.graph_editor: "StageGraphEditor" = graph_editor

        self.create_actions()
        self.create_widgets()
        self.create_layouts()
        self.create_connections()

    def create_actions(self):
        pass

    def create_widgets(self):
        pass

    def create_layouts(self):
        pass

    def create_connections(self):
        pass

    @property
    def stage(self):
        return self.graph_editor.stage
