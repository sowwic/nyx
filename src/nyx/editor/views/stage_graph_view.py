import pathlib
from PySide2 import QtGui
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
        self.last_saved_undo_index = 0

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

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self.maybe_save():
            event.accept()
        else:
            event.ignore()
            return

        return super().closeEvent(event)

    def is_modified(self):
        self.last_saved_undo_index != self.stage.undo_stack.index()

    def update_title(self):
        if not self.stage.file_path:
            title = self.DEFAULT_TITLE
        else:
            title = self.stage.file_path.name

        if self.stage.undo_stack.index():
            title += "*"
        self.setWindowTitle(title)

    def maybe_save(self):
        if not self.is_modified():
            return True

        res = QtWidgets.QMessageBox.warning(self, 'Warning: Graph is not saved',
                                            'Save changes to current graph?',
                                            QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel)
        if res == QtWidgets.QMessageBox.Save:
            return self.on_stage_save()
        if res == QtWidgets.QMessageBox.Cancel:
            return False
        return True

    def on_stage_new(self):
        if not self.maybe_save():
            self.set_stage(Stage)
            self.last_saved_undo_index = self.stage.undo_stack.index()

    def on_stage_open(self):
        if not self.maybe_save():
            return

        file_filter = "Nyx graph (*.nyx)"
        file_path = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open Nyx Graph", None, file_filter)[0]
        if not file_path:
            return False
        self.set_stage(Stage())
        self.stage.import_json(file_path)
        self.last_saved_undo_index = self.stage.undo_stack.index()
        return True

    def on_stage_save(self):
        if self.stage.file_path is not None:
            self.stage.export_json(self.stage.file_path)
        else:
            self.on_stage_save_as()
        self.last_saved_undo_index = self.stage.undo_stack.index()

    def on_stage_save_as(self):
        file_filter = "Nyx stage (*.nyx)"
        file_path = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save build graph to file', None, file_filter)[0]
        if not file_path:
            return False
        self.stage.export_json(file_path)
        self.last_saved_undo_index = self.stage.undo_stack.index()
        return True
