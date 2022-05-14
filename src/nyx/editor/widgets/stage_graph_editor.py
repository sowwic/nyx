import typing
import pathlib
from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets

from nyx.core import Stage
from nyx import get_main_logger
from nyx.editor.graphics.graphics_scene import NyxGraphicsScene
from nyx.editor.views.stage_graph_view import StageGraphView
from nyx.editor.widgets.graph_scope_widget import GraphScopeWidget

if typing.TYPE_CHECKING:
    from nyx.core import Node
    from nyx.editor.main_window import NyxEditorMainWindow


LOGGER = get_main_logger()


class StageGraphEditor(QtWidgets.QWidget):

    DEFAULT_TITLE = "Untitled"

    scope_changed = QtCore.Signal(pathlib.PurePosixPath)

    def __init__(self, stage: Stage = None, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent=parent)
        self.main_window: "NyxEditorMainWindow" = QtWidgets.QApplication.instance().main_window()
        self.tree_view = self.main_window.stage_tree_view
        self.last_saved_undo_index = 0
        self.__stage: Stage = None
        self.set_stage(stage, create_connections=False)
        self.__scope_path = self.stage.ROOT_ITEM_PATH

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

    def set_stage(self, stage: Stage, create_connections=True):
        old_stage = self.stage
        if stage is None:
            stage = Stage()
        self.__stage = stage
        self.update_title()
        if create_connections:
            self.create_stage_connections()
        if old_stage:
            old_stage.deleteLater()

    def create_actions(self):
        """Create and setup actions."""
        pass

    def create_widgets(self):
        """Create and setup widgets."""
        self.graph_scope_widget = GraphScopeWidget(self)
        self.gr_scene = NyxGraphicsScene()
        self.gr_view = StageGraphView(self)

    def create_layouts(self):
        """Create and populate layouts."""
        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)

        self.main_layout.addWidget(self.graph_scope_widget)
        self.main_layout.addWidget(self.gr_view)

    def create_stage_connections(self):
        """Create connections between graph widgets and stage."""
        self.stage.undo_stack.indexChanged.connect(self.update_title)
        self.tree_view.node_doubleclicked.connect(self.set_scope_path)
        self.stage.node_deleted.connect(self._handle_scope_path_at_node_deletion)

    def create_connections(self):
        """Create signal to slot connections."""
        self.create_stage_connections()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Overridden close event.

        - Prompts stage save.

        Args:
            event (QtGui.QCloseEvent): close event.

        Returns:
            None: super return call.
        """
        if self.maybe_save():
            event.accept()
        else:
            event.ignore()
            return

        return super().closeEvent(event)

    def update_title(self):
        if not self.stage.file_path:
            title = self.DEFAULT_TITLE
        else:
            title = self.stage.file_path.name

        if self.stage.is_modified():
            title += "*"
        self.setWindowTitle(title)

    def maybe_save(self):
        """Prompt user to save current scene it is new or has been modified.

        Returns:
            bool: True if user saved the scene or chose discard option.
        """
        if self.stage.is_new() or not self.stage.is_modified():
            return True

        stage_title = self.DEFAULT_TITLE if not self.stage.file_path else self.stage.file_path.name
        res = QtWidgets.QMessageBox.warning(self, 'Stage is not saved',
                                            f'Save changes to "{stage_title}"?',
                                            QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel)
        if res == QtWidgets.QMessageBox.Save:
            return self.on_stage_save()
        if res == QtWidgets.QMessageBox.Cancel:
            return False
        return True

    def on_stage_new(self):
        if not self.maybe_save():
            self.set_stage(Stage)

    def on_stage_open(self):
        if not self.maybe_save():
            return

        file_filter = "Nyx Stage (*.nyx)"
        file_path = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open Stage", None, file_filter)[0]
        if not file_path:
            return False

        new_stage = Stage()
        new_stage.import_json(file_path)
        self.set_stage(new_stage)
        return True

    def on_stage_save(self):
        if self.stage.file_path is not None:
            self.stage.export_json(self.stage.file_path)
        else:
            self.on_stage_save_as()
        self.update_title()

    def on_stage_save_as(self):
        file_filter = "Nyx Stage (*.nyx)"
        file_path = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save stage to file', None, file_filter)[0]
        if not file_path:
            return False
        self.stage.export_json(file_path)
        self.update_title()
        return True

    def get_scope_path(self) -> pathlib.PurePosixPath:
        return self.__scope_path

    def set_scope_path(self, scope: "Node | pathlib.PurePosixPath | str", silent=False) -> None:
        previous_scope = self.get_scope_path()

        node = self.stage.node(scope)
        if node:
            new_scope = node.path
        elif scope and pathlib.PurePosixPath(scope) == self.stage.ROOT_ITEM_PATH:
            new_scope = self.stage.ROOT_ITEM_PATH
        else:
            new_scope = previous_scope

        self.__scope_path = new_scope
        LOGGER.debug(f"Set scope to: {self.__scope_path}")
        if not silent:
            self.scope_changed.emit(self.__scope_path)

    def scope_back(self) -> None:
        self.set_scope_path(self.get_scope_path().parent)

    def _handle_scope_path_at_node_deletion(self, deleted_node_path):
        current_scope = self.get_scope_path()
        if current_scope == deleted_node_path or deleted_node_path in current_scope.parents:
            self.set_scope_path(self.stage.ROOT_ITEM_PATH)
