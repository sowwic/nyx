import pathlib
from PySide2 import QtWidgets

from nyx.core import Stage
from nyx import get_main_logger
from nyx.editor.graphics.graphics_scene import NyxGraphicsScene


LOGGER = get_main_logger()


class StageGraphView(QtWidgets.QGraphicsView):

    DEFAULT_TITLE = "Untitled"

    def __init__(self, stage: Stage = None, parent: QtWidgets.QWidget = None) -> None:

        super().__init__(NyxGraphicsScene(), parent=parent)
        self.setScene(NyxGraphicsScene())
        self.set_stage(stage)

        self.create_actions()
        self.create_widgets()
        self.create_layouts()
        self.create_connections()

    @classmethod
    def from_json_file(cls, file_path: "pathlib.Path | str"):
        stage = Stage()
        stage.import_json(file_path)
        widget = cls(stage)
        return widget

    @property
    def stage(self):
        return self.__stage

    def set_stage(self, stage: Stage):
        if stage is None:
            stage = Stage()
        self.__stage = stage
        self.update_title()

    def create_actions(self):
        pass

    def create_widgets(self):
        pass

    def create_layouts(self):
        pass

    def create_connections(self):
        self.stage.undo_stack.indexChanged.connect(self.update_title)

    def update_title(self, *args):
        if not self.stage.file_path:
            title = self.DEFAULT_TITLE
        else:
            title = self.stage.file_path.name

        if self.stage.undo_stack.index():
            title += "*"
        self.setWindowTitle(title)
