import logging
import pathlib
import typing

import shiboken6
from PySide6 import QtCore, QtGui, QtWidgets

from nyx.core import Stage
from nyx.core.exceptions import StageObjectQueryError
from nyx.editor.graphics.graphics_stage import GraphicsStage
from nyx.editor.views.stage_graph_view import StageGraphView
from nyx.editor.widgets.graph_scope_widget import GraphScopeWidget
from nyx.editor.widgets.dialogs.popup_nodes_palette import PopupNodesPalette
from nyx.utils import pyside_fn

if typing.TYPE_CHECKING:
    from nyx.core.node import NodeLike, Node
    from nyx.editor.main_window import NyxEditorMainWindow


LOGGER = logging.getLogger(__name__)


class StageGraphEditor(QtWidgets.QWidget):
    DEFAULT_TITLE = "Untitled"

    stage_changed = QtCore.Signal(Stage)
    scope_changed = QtCore.Signal(pathlib.PurePosixPath)

    def __init__(
        self, stage: Stage | None = None, parent: QtWidgets.QWidget | None = None
    ) -> None:
        super().__init__(parent=parent)
        self.main_window: NyxEditorMainWindow = pyside_fn.find_nyx_editor_window()
        self.tree_view = self.main_window.stage_tree_view
        self.last_saved_undo_index = 0
        self._selection_model = QtCore.QItemSelectionModel()
        self._stage: Stage = None
        self.set_stage(stage, create_connections=False)
        self._scope_path = self.stage.root_node.path

        self.create_actions()
        self.create_widgets()
        self.create_layouts()
        self.create_connections()

        self.gr_stage.rebuild_current_scope()
        self.update_title()

    @classmethod
    def from_json_file(cls, file_path: pathlib.Path | str):
        stage = Stage()
        stage.import_json(file_path)
        widget = cls(stage)
        return widget

    @property
    def stage(self) -> Stage:
        return self._stage

    @property
    def selection_model(self) -> QtCore.QItemSelectionModel:
        return self._selection_model

    def set_stage(self, stage: Stage | None, create_connections=True):
        old_stage = self.stage
        if stage is None:
            stage = Stage()
        self._stage = stage
        self._selection_model.setModel(stage)
        self.stage_changed.emit(stage)
        if create_connections:
            self.create_stage_connections()
        if old_stage:
            old_stage.deleteLater()

    def create_actions(self):
        """Create and setup actions."""
        self._show_nodes_palette_action = QtGui.QAction("Add Node...", self)
        self._show_nodes_palette_action.setShortcut(
            QtGui.QKeySequence(QtCore.Qt.Key.Key_Tab)
        )
        self._show_nodes_palette_action.setShortcutContext(
            QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut
        )
        self._show_nodes_palette_action.triggered.connect(
            self._shows_popup_nodes_palette
        )
        self.addAction(self._show_nodes_palette_action)

    def create_widgets(self):
        """Create and setup widgets."""
        self.graph_scope_widget = GraphScopeWidget(self)
        self.gr_stage = GraphicsStage(self)
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
        # Stage connections
        self.stage.undo_stack.indexChanged.connect(self.update_title)
        self.stage.undo_stack.indexChanged.connect(self.gr_stage.rebuild_current_scope)
        self.stage.node_deleted.connect(self._handle_scope_path_at_node_deletion)
        # Selection model connections
        self.selection_model.selectionChanged.connect(
            self.gr_stage.on_selection_model_selection_changed
        )

    def create_connections(self):
        """Create signal to slot connections."""
        self.create_stage_connections()
        self.stage_changed.connect(self.update_title)
        self.tree_view.node_doubleclicked.connect(self.set_scope_path)
        self.scope_changed.connect(self.gr_stage.rebuild_scope)

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

        stage_title = (
            self.DEFAULT_TITLE if not self.stage.file_path else self.stage.file_path.name
        )
        res = QtWidgets.QMessageBox.warning(
            self,
            "Stage is not saved",
            f'Save changes to "{stage_title}"?',
            QtWidgets.QMessageBox.Save
            | QtWidgets.QMessageBox.Discard
            | QtWidgets.QMessageBox.Cancel,
        )
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
            self, "Open Stage", None, file_filter
        )[0]
        if not file_path:
            return False

        self.scope_root()
        new_stage = Stage()
        new_stage.import_json(file_path)
        self.set_stage(new_stage)
        self.gr_stage.rebuild_current_scope()
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
            self, "Save stage to file", None, file_filter
        )[0]
        if not file_path:
            return False
        self.stage.export_json(file_path)
        self.update_title()
        return True

    def get_scope_path(self) -> pathlib.PurePosixPath:
        return self._scope_path

    def get_next_valid_scope(self, scope: NodeLike):
        scope_path = self.stage.pathify(scope)
        paths_to_check = [scope_path]
        paths_to_check.extend(scope_path.parents)
        for each_path in paths_to_check:
            try:
                self.stage.get_object(each_path)
                return each_path
            except StageObjectQueryError:
                continue

    def make_scope_valid(self):
        if not shiboken6.isValid(self.stage):
            return
        self.set_scope_path(self.get_next_valid_scope(self._scope_path))

    def set_scope_path(
        self, scope: Node | pathlib.PurePosixPath | str, silent=False
    ) -> None:
        new_scope = self.get_next_valid_scope(scope)

        self._scope_path = new_scope
        LOGGER.debug(f"Set scope to: {self._scope_path}")
        if not silent:
            self.scope_changed.emit(self._scope_path)

    def scope_back(self) -> None:
        self.set_scope_path(self.get_scope_path().parent)

    def scope_root(self) -> None:
        self.set_scope_path(self.stage.root_node.path)

    def filter_nodes_by_scope(self, nodes: list[Node]) -> list[Node]:
        """Filter nodes by scope.

        Args:
            nodes (list[Node]): Nodes to filter.

        Returns:
            list[Node]: Filtered nodes.

        """
        current_scope_node = self.stage.get_object(self.get_scope_path())
        scope_child_nodes = self.stage.list_children(current_scope_node)
        filtered_nodes = list(set(nodes).intersection(set(scope_child_nodes)))
        return filtered_nodes

    def _handle_scope_path_at_node_deletion(self, deleted_node_path):
        current_scope = self.get_scope_path()
        if (
            current_scope == deleted_node_path
            or deleted_node_path in current_scope.parents
        ):
            self.make_scope_valid()

    def list_selected_nodes(self) -> list[Node]:
        """List selected nodes.

        Returns:
            list[Node]: selected nodes

        """
        selected_indexes = self.selection_model.selectedIndexes()
        return [self.stage.itemFromIndex(index) for index in selected_indexes]

    def _shows_popup_nodes_palette(self):
        point_under_cursor_in_gr_view = self.gr_view.viewport().mapFromGlobal(
            QtGui.QCursor.pos()
        )
        if not self.gr_view.viewport().rect().contains(point_under_cursor_in_gr_view):
            return
        palette = PopupNodesPalette.popup()
