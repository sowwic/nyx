"""
This module defines the GraphicsStage class,
which is a QGraphicsScene that manages the visual representation of
nodes and edges in the graph editor.
"""

import logging
import math
import pathlib
import typing
from collections import deque
from uuid import UUID

import shiboken6
from PySide6 import QtCore, QtGui, QtWidgets

from nyx.core.exceptions import StageObjectQueryError
from nyx.core.stage_object import StageObject
from nyx.editor.graphics.graphics_node import GraphicsNode

if typing.TYPE_CHECKING:
    from nyx.core.node import Node
    from nyx.core.stage import Stage
    from nyx.editor.widgets.stage_graph_editor import StageGraphEditor

LOGGER = logging.getLogger(__name__)


class GraphicsStage(QtWidgets.QGraphicsScene):
    """`GraphicsStage` is a `QGraphicsScene` that manages
    the visual representation of nodes and edges in the graph editor."""

    def __init__(
        self, graph_editor: StageGraphEditor, parent: QtCore.QObject | None = None
    ):
        """Initializes the GraphicsStage with the given graph editor and parent.

        Args:
            graph_editor: The graph editor associated with this graphics stage.
            parent (QObject, optional): The parent object for this graphics stage.
        """
        super().__init__(parent=parent)

        self._graph_editor = graph_editor
        self._gr_nodes: dict[UUID, GraphicsNode] = {}
        self._scope_path: pathlib.PurePosixPath | None = None

        # Settings
        self.grid_size = 20
        self.grid_squares = 5
        self.scene_width = self.scene_height = 64000
        # NOTE: calling self.setSceneRect(QtCore.QRect) again disables view scrolling
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
        self.stage.itemChanged.connect(self.on_node_changed)

    @property
    def graph_editor(self) -> StageGraphEditor:
        """Returns the graph editor associated with this graphics stage."""
        return self._graph_editor

    @property
    def stage(self) -> Stage:
        """Returns the stage from the graph editor."""
        return self.graph_editor.stage

    @property
    def selection_model(self):
        """Returns the selection model from the graph editor."""
        return self.graph_editor.selection_model

    # ======== Events ========= #

    def dragMoveEvent(self, event):
        """Ignore drag moves so the parent doesn't handle them.

        Args:
            event (QtWidgets.QGraphicsSceneDragDropEvent): event.
        """
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

    # ======== Nodes ========= #

    def gr_nodes(self) -> list[GraphicsNode]:
        """Returns all GraphicsNode items in the scene."""
        return list(self._gr_nodes.values())

    def get_gr_node(
        self, node: Node | UUID | pathlib.PurePosixPath | str
    ) -> GraphicsNode | None:
        """Returns the GraphicsNode drawn for the given node, if it is in scope.

        Args:
            node: node, its uuid or its path.
        """
        if isinstance(node, StageObject):
            uuid = node.uuid
        elif isinstance(node, UUID):
            uuid = node
        else:
            try:
                found = self.stage.get_object(node)
            except StageObjectQueryError:
                found = None
            if found is None:
                LOGGER.warning(f"Failed to find gr node for {node}")
                return None
            uuid = found.uuid
        return self._gr_nodes.get(uuid)

    def selected_gr_nodes(self):
        """Returns a generator of all selected GraphicsNode items in the scene."""
        return (item for item in self.selectedItems() if isinstance(item, GraphicsNode))

    def list_selected_node_paths(self):
        """Returns a list of paths for the currently selected GraphicsNode items."""
        return [gr_node.node.path for gr_node in self.selected_gr_nodes()]

    def is_gr_node_selection_empty(self):
        """Check if there are no selected GraphicsNode items in the scene."""
        return next(self.selected_gr_nodes(), None) is None

    def get_last_selected_gr_node(self):
        """Returns the last selected GraphicsNode item in the scene"""
        if self.is_gr_node_selection_empty():
            return None
        return deque(self.selected_gr_nodes(), maxlen=1).pop()

    def is_in_scope(self, node: Node) -> bool:
        """Check if the node is a direct child of the scope being drawn.

        Args:
            node (Node): node to check.
        """
        if self._scope_path is None:
            return False
        parent = node.parent()
        return parent is not None and parent.path == self._scope_path

    def add_node(self, node: Node | pathlib.PurePosixPath | str) -> GraphicsNode | None:
        """Adds a GraphicsNode item to the scene for the given node.

        Only direct children of the scope being drawn get an item.

        Args:
            node: The node to create a GraphicsNode for.

        Returns:
            GraphicsNode | None: item for the node, None if the node is out of scope.
        """
        node = self.stage.get_object(node)
        if not self.is_in_scope(node):
            LOGGER.debug(f"Skipping {node.path}: not a child of {self._scope_path}")
            return None

        gr_node = self._gr_nodes.get(node.uuid)
        if gr_node is not None:
            if gr_node.node is node:
                return gr_node
            self.remove_node(node.uuid)

        gr_node = GraphicsNode(node)
        self._gr_nodes[node.uuid] = gr_node
        self.addItem(gr_node)
        return gr_node

    def remove_node(self, node: Node | UUID) -> None:
        """Removes the GraphicsNode item of the given node, if there is one.

        Args:
            node (Node | UUID): node or its uuid.
        """
        gr_node = self._gr_nodes.pop(getattr(node, "uuid", node), None)
        if gr_node is not None:
            self.removeItem(gr_node)

    def clear_nodes(self):
        """Removes all GraphicsNode items from the scene."""
        for uuid in list(self._gr_nodes):
            self.remove_node(uuid)

    def build_nodes(self, scope_node: Node):
        """Make the GraphicsNode items match the child nodes of the scope node.

        Items of nodes that are gone (or were replaced by another instance) are
        removed, missing ones are created and existing ones are refreshed.

        Args:
            scope_node (Node): node being drawn.
        """
        children = {node.uuid: node for node in self.stage.list_children(scope_node)}
        for uuid, gr_node in list(self._gr_nodes.items()):
            if children.get(uuid) is not gr_node.node:
                self.remove_node(uuid)

        for uuid, node in children.items():
            gr_node = self._gr_nodes.get(uuid)
            if gr_node is None:
                self.add_node(node)
            else:
                gr_node.refresh()

    # ======== Links ========= #

    def clear_links(self):
        """Removes all GraphicsEdge items from the scene."""
        LOGGER.debug("TODO: cleaning edges")

    def build_links(self, scope_node: Node):
        """
        Builds GraphicsEdge items for all connections between child nodes for given node.

        Must run after `build_nodes`: links attach to the plugs of the node items.
        """
        # TODO: Build graphics edges
        pass

    # ======== Scope ========= #

    def rebuild_scope(self, scope_path: pathlib.PurePosixPath):
        """Update the scene to show the children of the scope node.

        Switching to another scope drops all items. Rebuilding the same scope
        only adds, removes and refreshes what changed. Nodes are always built
        before links, and links are removed before nodes.

        Args:
            scope_path (pathlib.PurePosixPath): The path of the scope to rebuild.
        """
        if not shiboken6.isValid(self.stage):
            return

        if scope_path is None:
            return

        LOGGER.debug(f"Rebuilding scope: {scope_path}")
        previous_selection = self.list_selected_node_paths()
        self.clear_links()
        if scope_path != self._scope_path:
            self.clear_nodes()
            self._scope_path = scope_path
        scope_node = self.stage.get_object(scope_path)
        self.build_nodes(scope_node)
        self.build_links(scope_node)
        self._restore_selection(previous_selection)

    def _restore_selection(self, paths: list[pathlib.PurePosixPath]):
        """Select the items of nodes that are still drawn.

        Args:
            paths (list[pathlib.PurePosixPath]): node paths to select.
        """
        index_selection = QtCore.QItemSelection()
        for path in paths:
            if not path:
                continue
            try:
                node = self.stage.get_object(path)
            except StageObjectQueryError:
                node = None
            if node is None or node.uuid not in self._gr_nodes:
                continue
            index_selection.select(node.index(), node.index())
        if index_selection.isEmpty():
            return
        self.selection_model.select(index_selection, QtCore.QItemSelectionModel.Select)

    def rebuild_current_scope(self):
        """Rebuilds the scene for the current scope, preserving the selection."""
        self.graph_editor.make_scope_valid()
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
                gr_node = self._gr_nodes.get(node.uuid)
                if gr_node is None:
                    LOGGER.warning(f"Missing graphics node for selection: {node}")
                    continue
                gr_node.setSelected(True)
        # Ensure signals are always unblocked even on early return
        finally:
            self.blockSignals(False)

    def on_node_changed(self, node: Node):
        """Refresh the item of a node whose data changed (position, name, ...).

        Args:
            node (Node): changed node.
        """
        gr_node = self._gr_nodes.get(getattr(node, "uuid", None))
        if gr_node is not None and gr_node.node is node:
            gr_node.refresh()

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
