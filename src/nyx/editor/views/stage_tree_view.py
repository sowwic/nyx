import functools
import typing
import logging
from collections import deque

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

from nyx.core import commands
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
        self.setModel(stage)
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
            enabled_fn=lambda: bool(self.selected_nodes()),
        )

    def create_connections(self):
        """Connect signals."""
        self.doubleClicked.connect(self._emit_doubledclicked_item)
        self.customContextMenuRequested.connect(self.show_context_menu)

    @property
    def stage(self) -> Stage:
        """Stage: stage shown by the view."""
        return self.model()

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
        self.setModel(stage)
        if stage is None:
            return
        self.setRootIndex(stage.root_node.index())

    def _emit_doubledclicked_item(self, index):
        """Emit `node_doubleclicked` for a double clicked index.

        Args:
            index (QtCore.QModelIndex): double clicked index.
        """
        if not self.stage:
            return
        node = self.stage.itemFromIndex(index)
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
            deque[Node]: selected nodes.
        """
        nodes = deque()
        for index in self.selectedIndexes():
            nodes.append(self.stage.itemFromIndex(index))

        return nodes

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
            if not self.indexAt(event.pos()).isValid():
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
        self.current_stage_graph.gr_view.focus_on_selected_nodes()

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
        menu.exec_(self.mapToGlobal(point))
