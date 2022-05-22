import math
import typing
import pathlib
from collections import deque

from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets

from nyx import get_main_logger
from nyx.editor.graphics.graphics_node import GraphicsNode
if typing.TYPE_CHECKING:
    from nyx.core import Node
    from nyx.editor.widgets.stage_graph_editor import StageGraphEditor

LOGGER = get_main_logger()


class GraphicsStage(QtWidgets.QGraphicsScene):

    nodes_selection_cleared = QtCore.Signal()
    nodes_selection_changed = QtCore.Signal(list)

    def __init__(self, graph_editor: "StageGraphEditor", parent=None):
        super().__init__(parent=parent)

        self.__graph_editor = graph_editor
        self._previous_selected_paths: list[pathlib.PurePosixPath] = []

        # Settings
        self.grid_size = 20
        self.grid_squares = 5
        self.scene_width = self.scene_height = 64000
        # ? Note: calling self.setSceneRect(QtCore.QRect) again disables QGraphicsView scrolling
        self.set_scene_size(self.scene_width, self.scene_height)
        # Colors
        self._color_background = QtGui.QColor("#393939")
        self._color_light = QtGui.QColor("#2f2f2f")
        self._color_dark = QtGui.QColor("#292929")
        self._pen_light = QtGui.QPen(self._color_light)
        self._pen_light.setWidth(1)
        self._pen_dark = QtGui.QPen(self._color_dark)
        self._pen_dark.setWidth(2)
        self.setBackgroundBrush(self._color_background)

        self.create_connections()

    def create_connections(self):
        self.selectionChanged.connect(self.on_selection_changed)

    @property
    def graph_editor(self):
        return self.__graph_editor

    @property
    def stage(self):
        return self.graph_editor.stage

    # ======== Events ========= #

    def dragMoveEvent(self, event):
        # Disable parent event
        pass

    # ======== Methods ========= #

    def set_scene_size(self, width, height):
        self.setSceneRect(-width // 2, -height // 2, width, height)

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        left = int(math.floor(rect.left()))
        right = int(math.ceil(rect.right()))
        top = int(math.floor(rect.top()))
        bottom = int(math.ceil(rect.bottom()))

        first_left = left - (left % self.grid_size)
        first_top = top - (top % self.grid_size)

        # Compute line drawing
        lines_light, lines_dark = [], []
        for x in range(first_left, right, self.grid_size):
            if (x % (self.grid_size * self.grid_squares)):
                lines_light.append(QtCore.QLine(x, top, x, bottom))
            else:
                lines_dark.append(QtCore.QLine(x, top, x, bottom))

        for y in range(first_top, bottom, self.grid_size):
            if (y % (self.grid_size * self.grid_squares)):
                lines_light.append(QtCore.QLine(left, y, right, y))
            else:
                lines_dark.append(QtCore.QLine(left, y, right, y))

        # Draw lines
        painter.setPen(self._pen_light)
        painter.drawLines(lines_light)
        painter.setPen(self._pen_dark)
        painter.drawLines(lines_dark)

    def gr_nodes(self):
        return (item for item in self.items() if isinstance(item, GraphicsNode))

    def get_gr_node(self, node: "Node | pathlib.PurePosixPath | str"):
        input_node = node
        node = self.stage.node(node)
        if not node:
            LOGGER.exception(f"Failed to find gr node for {input_node}")
            return
        return node.gr_node

    def selected_gr_nodes(self):
        return (item for item in self.selectedItems() if isinstance(item, GraphicsNode))

    def list_selected_node_paths(self):
        return [gr_node.node.cached_path for gr_node in self.selected_gr_nodes()]

    def is_gr_node_selection_empty(self):
        return next(self.selected_gr_nodes(), None) is None

    def get_last_selected_gr_node(self):
        if self.is_gr_node_selection_empty():
            return None
        return deque(self.selected_gr_nodes(), maxlen=1).pop()

    def clear_nodes(self):
        for gr_node in self.gr_nodes():
            gr_node.node.gr_node = None
            self.removeItem(gr_node)

    def clear_edges(self):
        LOGGER.debug("TODO: cleaning edges")

    def add_node(self, node: "Node | pathlib.PurePosixPath | str"):
        node = self.stage.node(node)
        gr_node = GraphicsNode(node)
        self.addItem(gr_node)

    def build_nodes(self, scope_node: "Node"):
        child_nodes = self.stage.list_children(scope_node)
        for node in child_nodes:
            self.add_node(node)

    def build_edges(self, scope_node: "Node"):
        # TODO: Build graphics edges
        pass

    def rebuild_scope(self, scope_path: pathlib.PurePosixPath):
        LOGGER.debug(f"Rebuilding scope: {scope_path}")
        previous_selection = self.list_selected_node_paths()
        self.clear_edges()
        self.clear_nodes()
        scope_node = self.stage.node(scope_path)
        self.build_nodes(scope_node)
        self.build_edges(scope_node)
        for path in previous_selection:
            node = self.stage.node(path)
            if not node or not node.gr_node:
                continue
            node.gr_node.setSelected(True)

    def rebuild_current_scope(self):
        self.rebuild_scope(self.graph_editor.get_scope_path())

    def on_selection_changed(self):
        selected_paths = self.list_selected_node_paths()
        if not selected_paths:
            self.nodes_selection_cleared.emit()
            self._previous_selected_paths.clear()
        elif set(selected_paths) == set(self._previous_selected_paths):
            pass
        else:
            self._previous_selected_paths = selected_paths
            self.nodes_selection_changed.emit(selected_paths)

    def on_tree_view_selection_changed(self):
        self.blockSignals(True)
        self.clearSelection()
        tree_view_selected_nodes = self.graph_editor.tree_view.selected_nodes()
        current_scope_node = self.stage.node(self.graph_editor.get_scope_path())
        scope_child_nodes = self.stage.list_children(current_scope_node)
        scope_selected_nodes = list(
            set(tree_view_selected_nodes).intersection(set(scope_child_nodes)))
        if not scope_selected_nodes:
            return

        for node in scope_selected_nodes:
            if node.gr_node is None:
                LOGGER.exception(f"Missing graphics node for selection: {node}")
                continue
            node.gr_node.setSelected(True)

        self.blockSignals(False)

    def start_selected_node_rename(self):
        gr_node = self.get_last_selected_gr_node()
        if not gr_node:
            return
        gr_node.title_item.edit()
