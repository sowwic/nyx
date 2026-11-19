import functools
import typing
import logging
from collections import deque

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

from nyx.core import commands
from nyx.core.models.stage_filter_model import StageFilterModel
from nyx.editor.core.action_router import ACTION_ROUTER
from nyx.editor.core.actions import ActionId
from nyx.editor.utils import clipboard, context_menus
from nyx.editor.views.node_item_delegate import NodeItemDelegate
from nyx.utils import pyside_fn

if typing.TYPE_CHECKING:
    from nyx.core import Stage
    from nyx.core import Node
    from nyx.editor.main_window import NyxEditorMainWindow

LOGGER = logging.getLogger(__name__)


class StageTreeView(QtWidgets.QTreeView):
    """Tree view of the nodes of a stage.

    The view shows the stage through a `StageFilterModel`, so only the nodes that match
    the filter text are listed. Its selection is the part of the selection model of the
    stage that is listed: nodes the filter hides stay selected in the model.

    Attributes:
        selection_changed: emitted when the selection changes
        nodes_selected: emitted with the nodes that became selected
        nodes_deselected: emitted with the nodes that were deselected
        node_doubleclicked: emitted with the node that was double clicked
    """

    selection_changed = QtCore.Signal()
    nodes_selected = QtCore.Signal(list)
    nodes_deselected = QtCore.Signal(list)
    node_doubleclicked = QtCore.Signal(QtGui.QStandardItem)

    def __init__(
        self, stage: Stage | None = None, parent: QtWidgets.QWidget | None = None
    ) -> None:
        """Initialize StageTreeView.

        Args:
            stage (Stage | None): stage to show.
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(parent)
        self._source_selection_model: QtCore.QItemSelectionModel | None = None
        self._is_syncing_selection = False

        self._filter_model = StageFilterModel(self)
        # Before the selection model exists, so that its handlers of the removed rows
        # run after this one
        self._filter_model.rowsAboutToBeRemoved.connect(self._begin_syncing_selection)
        self._filter_model.rowsRemoved.connect(self._end_syncing_selection)
        self.setModel(self._filter_model)
        self.set_stage(stage)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setHeaderHidden(True)
        self.setSelectionMode(self.SelectionMode.ExtendedSelection)
        self.setExpandsOnDoubleClick(False)
        self.setEditTriggers(StageTreeView.NoEditTriggers)
        self.setIconSize(QtCore.QSize(16, 16))
        self.setItemDelegate(NodeItemDelegate(self))

        self.create_actions()
        self.create_connections()

    def create_actions(self):
        """Register handlers of the node actions for this view."""
        register = functools.partial(ACTION_ROUTER.register_handler, scope=self)
        register(ActionId.CREATE_NODE, self.create_new_node)
        register(ActionId.DELETE_NODE, self.delete_selected_node)
        register(ActionId.COPY, self.copy_selected_nodes)
        register(ActionId.CUT, self.cut_selected_nodes)
        register(ActionId.PASTE, self.paste_nodes_from_clipboard)
        register(ActionId.COPY_NODE_PATH, self.copy_selected_node_path)
        register(
            ActionId.FOCUS_SELECTED,
            self.focus_on_selected_nodes,
            condition=lambda: bool(self.selected_nodes()),
        )

    def create_connections(self):
        """Connect signals."""
        self.doubleClicked.connect(self._emit_doubledclicked_item)
        self.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self.customContextMenuRequested.connect(self.show_context_menu)

    @property
    def stage(self) -> Stage | None:
        """Stage | None: stage shown by the view."""
        return self._filter_model.sourceModel()

    @property
    def filter_model(self) -> StageFilterModel:
        """StageFilterModel: model the view shows."""
        return self._filter_model

    @property
    def main_window(self) -> NyxEditorMainWindow:
        """NyxEditorMainWindow: editor main window."""
        return pyside_fn.find_nyx_editor_window()

    @property
    def current_stage_graph(self):
        """StageGraphEditor | None: editor of the active window."""
        return self.main_window.current_stage_graph

    def set_stage(self, stage: Stage | None):
        """Show a stage, rooted at its root node.

        Args:
            stage (Stage | None): stage to show, None to clear the view.
        """
        self._filter_model.setSourceModel(stage)
        if stage is None:
            return
        self.setRootIndex(self._filter_model.mapFromSource(stage.root_node.index()))

    def set_filter(self, text: str, tokens: list[str] | None = None):
        """Show only the nodes that match a search, and their parents.

        Args:
            text (str): part of a node name, empty for any node.
            tokens (list[str] | None): tokens like `tag:logic`, see
                `StageFilterModel.TOKEN_ROLES`.
        """
        self._filter_model.setQuery(text, tokens or [])
        # Rows that came back are not selected in the view yet
        self._sync_selection_from_source()
        if self._filter_model.is_active:
            self.expandAll()

    def index_of(self, node: Node) -> QtCore.QModelIndex:
        """Get the index of a node in the model the view shows.

        Args:
            node (Node): node of the stage.

        Returns:
            QtCore.QModelIndex: index, invalid if the filter hides the node.
        """
        return self._filter_model.mapFromSource(node.index())

    def set_selection_model(self, selection_model: QtCore.QItemSelectionModel | None):
        """Follow the selection of a selection model of the stage, and change it.

        Args:
            selection_model (QtCore.QItemSelectionModel | None): selection model of the
                stage, None to stop following.
        """
        if self._source_selection_model is not None:
            self._source_selection_model.selectionChanged.disconnect(
                self._sync_selection_from_source
            )
            self._source_selection_model.currentChanged.disconnect(
                self._on_source_current_changed
            )
        self._source_selection_model = selection_model
        if selection_model is not None:
            selection_model.selectionChanged.connect(self._sync_selection_from_source)
            selection_model.currentChanged.connect(self._on_source_current_changed)
        self._sync_selection_from_source()

    def _begin_syncing_selection(self):
        """Stop the changes of the selection of the view from reaching the stage."""
        self._is_syncing_selection = True

    def _end_syncing_selection(self):
        """Let the changes of the selection of the view reach the stage again."""
        self._is_syncing_selection = False

    def _is_following(self, selection_model: QtCore.QItemSelectionModel) -> bool:
        """Check if a selection model belongs to the stage shown.

        Args:
            selection_model (QtCore.QItemSelectionModel): selection model.

        Returns:
            bool: True if the selection model is of the stage the view shows.
        """
        stage = self.stage
        return stage is not None and selection_model.model() is stage

    def _sync_selection_from_source(self, *_):
        """Select in the view what the selection model of the stage has selected."""
        source = self._source_selection_model
        was_syncing = self._is_syncing_selection
        self._is_syncing_selection = True
        try:
            if source is None or not self._is_following(source):
                self.selectionModel().clearSelection()
                return
            self.selectionModel().select(
                self._filter_model.mapSelectionFromSource(source.selection()),
                QtCore.QItemSelectionModel.SelectionFlag.ClearAndSelect,
            )
        finally:
            self._is_syncing_selection = was_syncing

    def _on_source_current_changed(
        self, current: QtCore.QModelIndex, previous: QtCore.QModelIndex
    ):
        """Move the current index of the view along the one of the stage.

        Args:
            current (QtCore.QModelIndex): new current index of the stage.
            previous (QtCore.QModelIndex): previous current index of the stage.
        """
        source = self._source_selection_model
        if source is None or not self._is_following(source):
            return
        self.selectionModel().setCurrentIndex(
            self._filter_model.mapFromSource(current),
            QtCore.QItemSelectionModel.SelectionFlag.NoUpdate,
        )

    def _on_selection_changed(self, *_):
        """Select in the stage what is selected in the view."""
        source = self._source_selection_model
        if self._is_syncing_selection or source is None:
            return
        if not self._is_following(source):
            return
        source.select(
            self._filter_model.mapSelectionToSource(self.selectionModel().selection()),
            QtCore.QItemSelectionModel.SelectionFlag.ClearAndSelect,
        )

    def _emit_doubledclicked_item(self, index):
        """Emit `node_doubleclicked` for a double clicked index.

        Args:
            index (QtCore.QModelIndex): double clicked index.
        """
        if not self.stage:
            return
        node = self.stage.itemFromIndex(self._filter_model.mapToSource(index))
        self.node_doubleclicked.emit(node)

    def current_node(self) -> Node:
        """Get the last selected node.

        Returns:
            Node | None: node, None if nothing is selected.
        """
        if not self.stage:
            return None

        try:
            return self.selected_nodes()[-1]
        except IndexError:
            return None
        except Exception:
            LOGGER.exception("Treeview | Failed to get current item")
            return None

    def selected_nodes(self) -> deque[Node]:
        """Get the selected nodes.

        Returns:
            deque[Node]: selected nodes the filter doesn't hide.
        """
        source = self._source_selection_model
        if source is not None and self._is_following(source):
            # Read from the stage, the view is updated after the ones that listen to it
            source_indexes = [
                index
                for index in source.selectedIndexes()
                if self._filter_model.mapFromSource(index).isValid()
            ]
        else:
            source_indexes = [
                self._filter_model.mapToSource(index) for index in self.selectedIndexes()
            ]
        return deque(self.stage.itemFromIndex(index) for index in source_indexes)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """Delete the selected nodes on the Delete key.

        Args:
            event (QtGui.QKeyEvent): event.
        """
        if event.key() == QtCore.Qt.Key_Delete:
            self.delete_selected_node()
            return

        return super().keyPressEvent(event)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        """Clear the selection when clicking empty space.

        Args:
            event (QtGui.QMouseEvent): event.
        """
        if event.button() == QtCore.Qt.LeftButton:
            if not self.indexAt(event.position().toPoint()).isValid():
                self.selectionModel().clear()

        return super().mousePressEvent(event)

    def create_new_node(self):
        """Show the nodes palette."""
        if self.current_stage_graph is None:
            return
        self.current_stage_graph.show_nodes_palette_centered()

    def delete_selected_node(self):
        """Delete the selected nodes through an undoable command."""
        if not self.selected_nodes():
            return

        delete_cmd = commands.DeleteNodeCommand(self.stage, self.selected_nodes())
        self.stage.push_command(delete_cmd)

    def copy_selected_nodes(self):
        """Copy the selected nodes to the clipboard."""
        selected_nodes = self.selected_nodes()
        if not selected_nodes:
            return

        clipboard.serialize_nodes_to_clipboard(selected_nodes, delete=False)
        LOGGER.info("Copied selected nodes")

    def cut_selected_nodes(self):
        """Cut the selected nodes to the clipboard."""
        selected_nodes = self.selected_nodes()
        if not selected_nodes:
            return

        clipboard.serialize_nodes_to_clipboard(selected_nodes, delete=True)
        LOGGER.info("Cut selected nodes")

    def paste_nodes_from_clipboard(self):
        """Paste nodes from the clipboard under the current node."""
        serialized_nodes = clipboard.get_serialized_nodes_from_clipboard()
        if not serialized_nodes:
            LOGGER.warning("No nodes found in the clipboard!")
            return

        gr_view_center_position = self.current_stage_graph.gr_view.get_center_position()
        parent_node = self.current_node()
        paste_cmd = commands.PasteNodesCommand(
            stage=self.stage,
            serialize_nodes=serialized_nodes,
            position=gr_view_center_position,
            parent_node=parent_node,
        )
        self.stage.push_command(paste_cmd)

    def focus_on_selected_nodes(self):
        """Center the graph view on the nodes selected in the tree."""
        if self.current_stage_graph is None:
            return
        self.current_stage_graph.gr_view.edit_actions.focus_on_selected_nodes()

    def copy_selected_node_path(self):
        """Copy the path of the current node to the clipboard."""
        selected_node = self.current_node()
        if not selected_node:
            return
        QtWidgets.QApplication.clipboard().setText(selected_node.path.as_posix())
        LOGGER.info(f"Copied node path: {selected_node.path.as_posix()}")

    def show_context_menu(self, point: QtCore.QPoint):
        """Show the nodes context menu.

        Args:
            point (QtCore.QPoint): position in view coordinates.
        """
        menu = context_menus.build_nodes_context_menu(
            self, has_selection=bool(self.current_node())
        )
        context_menus.show_menu(menu, self.mapToGlobal(point))
