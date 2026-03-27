"""
This module defines the GraphicsStage class,
which is a QGraphicsScene that manages the visual representation of
nodes and edges in the graph editor.
"""

import math
import logging
import typing
import pathlib
from collections import deque

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets
import shiboken6

from nyx.editor.graphics.graphics_node import GraphicsNode

if typing.TYPE_CHECKING:
    from nyx.core import Node
    from nyx.editor.widgets.stage_graph_editor import StageGraphEditor

LOGGER = logging.getLogger(__name__)


class GraphicsStage(QtWidgets.QGraphicsScene):
    """GraphicsStage is a QGraphicsScene that manages the visual representation of nodes and edges in the graph editor."""

    def __init__(self, graph_editor: StageGraphEditor, parent=None):
        """Initializes the GraphicsStage with the given graph editor and parent.

        Args:
            graph_editor (StageGraphEditor): The graph editor associated with this graphics stage.
            parent (QObject, optional): The parent object for this graphics stage. Defaults to None.
        """
        super().__init__(parent=parent)

        self._graph_editor = graph_editor
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
        """Creates signal-slot connections for the graphics stage."""
        self.selectionChanged.connect(self.on_selection_changed)

    @property
    def graph_editor(self):
        """Returns the graph editor associated with this graphics stage."""
        return self._graph_editor

    @property
    def stage(self):
        """Returns the stage from the graph editor."""
        return self.graph_editor.stage

    @property
    def selection_model(self):
        """Returns the selection model from the graph editor."""
        return self.graph_editor.selection_model

    # ======== Events ========= #

    def dragMoveEvent(self, event):
        # Disable parent event
        pass

    # ======== Methods ========= #

    def set_scene_size(self, width, height):
        """Sets the scene rectangle to the specified width and height.

        Args:
            width (int): The width of the scene rectangle.
            height (int): The height of the scene rectangle.
        """
        self.setSceneRect(-width // 2, -height // 2, width, height)

    def drawBackground(self, painter, rect):
        """Draws a grid background for the scene."""
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
            if x % (self.grid_size * self.grid_squares):
                lines_light.append(QtCore.QLine(x, top, x, bottom))
            else:
                lines_dark.append(QtCore.QLine(x, top, x, bottom))

        for y in range(first_top, bottom, self.grid_size):
            if y % (self.grid_size * self.grid_squares):
                lines_light.append(QtCore.QLine(left, y, right, y))
            else:
                lines_dark.append(QtCore.QLine(left, y, right, y))

        # Draw lines
        painter.setPen(self._pen_light)
        painter.drawLines(lines_light)
        painter.setPen(self._pen_dark)
        painter.drawLines(lines_dark)

    def gr_nodes(self):
        """Returns a generator of all GraphicsNode items in the scene."""
        return (item for item in self.items() if isinstance(item, GraphicsNode))

    def get_gr_node(self, node: Node | pathlib.PurePosixPath | str):
        """Returns the GraphicsNode associated with the given node."""
        input_node = node
        node = self.stage.node(node)
        if not node:
            LOGGER.exception(f"Failed to find gr node for {input_node}")
            return
        return node.gr_node

    def selected_gr_nodes(self):
        """Returns a generator of all selected GraphicsNode items in the scene."""
        return (item for item in self.selectedItems() if isinstance(item, GraphicsNode))

    def list_selected_node_paths(self):
        """Returns a list of paths for the currently selected GraphicsNode items."""
        return [gr_node.node.cached_path for gr_node in self.selected_gr_nodes()]

    def is_gr_node_selection_empty(self):
        """Check if there are no selected GraphicsNode items in the scene."""
        return next(self.selected_gr_nodes(), None) is None

    def get_last_selected_gr_node(self):
        """Returns the last selected GraphicsNode item in the scene"""
        if self.is_gr_node_selection_empty():
            return None
        return deque(self.selected_gr_nodes(), maxlen=1).pop()

    def clear_nodes(self):
        """Removes all GraphicsNode items from the scene."""
        for gr_node in self.gr_nodes():
            gr_node._set_node(None)
            self.removeItem(gr_node)

    def clear_edges(self):
        """Removes all GraphicsEdge items from the scene."""
        LOGGER.debug("TODO: cleaning edges")

    def add_node(self, node: Node | pathlib.PurePosixPath | str):
        """Adds a GraphicsNode item to the scene for the given node.
        Args:
            node (Node | pathlib.PurePosixPath | str): The node to create a GraphicsNode for.
        """
        node = self.stage.node(node)
        gr_node = GraphicsNode(node)
        self.addItem(gr_node)

    def build_nodes(self, scope_node: Node):
        """Builds GraphicsNode items for all child nodes of the given scope node."""
        child_nodes = self.stage.list_children(scope_node)
        for node in child_nodes:
            self.add_node(node)

    def build_edges(self, scope_node: Node):
        """Builds GraphicsEdge items for all connections between child nodes of the given scope node."""
        # TODO: Build graphics edges
        pass

    def rebuild_scope(self, scope_path: pathlib.PurePosixPath):
        """Rebuilds the scene for the given scope path, preserving the selection.
        Args:
            scope_path (pathlib.PurePosixPath): The path of the scope to rebuild.
        """
        if not shiboken6.isValid(self.stage):
            return

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
            self.selection_model.select(node.index(), QtCore.QItemSelectionModel.Select)

    def rebuild_current_scope(self):
        """Rebuilds the scene for the current scope, preserving the selection."""
        self.rebuild_scope(self.graph_editor.get_scope_path())

    def on_selection_model_selection_changed(self):
        """Updates the scene selection to match the selection in the selection model."""
        self.blockSignals(True)
        try:
            self.clearSelection()
            selected_nodes = [
                self.stage.itemFromIndex(index)
                for index in self.selection_model.selectedIndexes()
            ]
            scope_selected_nodes = self.graph_editor.filter_nodes_by_scope(
                selected_nodes
            )
            if not scope_selected_nodes:
                return

            for node in scope_selected_nodes:
                if node.gr_node is None:
                    LOGGER.exception(f"Missing graphics node for selection: {node}")
                    continue
                node.gr_node.setSelected(True)
        # Ensure signals are always unblocked even on early return
        finally:
            self.blockSignals(False)

    def on_selection_changed(self):
        """Updates the selection model to match the scene selection."""
        gr_nodes = self.selected_gr_nodes()
        nodes = [gr_node.node for gr_node in gr_nodes]
        self.selection_model.clearSelection()
        for node in nodes:
            self.selection_model.select(node.index(), QtCore.QItemSelectionModel.Select)

    def start_selected_node_rename(self):
        """Starts editing the title of the last selected GraphicsNode item."""
        gr_node = self.get_last_selected_gr_node()
        if not gr_node:
            return
        gr_node.title_item.edit()
