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

from nyx.core import commands
from nyx.core.exceptions import NyxCommandValidationError, StageObjectQueryError
from nyx.core.link import Link
from nyx.core.stage_object import StageObject
from nyx.editor.graphics.graphics_link import GraphicsLink
from nyx.editor.graphics.graphics_node import GraphicsNode
from nyx.editor.graphics.graphics_plug import GraphicsPlug

if typing.TYPE_CHECKING:
    from nyx.core.node import Node
    from nyx.core.node_component import NodeComponent
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
        self._gr_links: dict[UUID, GraphicsLink] = {}
        self._drag_link: GraphicsLink | None = None
        self._drag_origin: tuple[GraphicsPlug, GraphicsPlug.Socket] | None = None
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

    def gr_links(self) -> list[GraphicsLink]:
        """Returns all GraphicsLink items of links in the scene."""
        return list(self._gr_links.values())

    def get_gr_link(self, link: Link | UUID) -> GraphicsLink | None:
        """Returns the GraphicsLink drawn for the given link, if there is one.

        Args:
            link (Link | UUID): link or its uuid.
        """
        return self._gr_links.get(getattr(link, "uuid", link))

    def add_link(
        self, link: Link, source_plug: GraphicsPlug, target_plug: GraphicsPlug
    ) -> GraphicsLink:
        """Adds a GraphicsLink item between two plugs.

        Args:
            link (Link): link to draw.
            source_plug (GraphicsPlug): plug the link starts at.
            target_plug (GraphicsPlug): plug the link ends at.

        Returns:
            GraphicsLink: new item.
        """
        self.remove_link(link.uuid)
        gr_link = GraphicsLink(source_plug, target_plug, link_uuid=link.uuid)
        gr_link.attach()
        self._gr_links[link.uuid] = gr_link
        self.addItem(gr_link)
        return gr_link

    def remove_link(self, link: GraphicsLink | Link | UUID) -> None:
        """Removes the GraphicsLink item of the given link, if there is one.

        Args:
            link (GraphicsLink | Link | UUID): item, link or link uuid.
        """
        gr_link = link if isinstance(link, GraphicsLink) else self.get_gr_link(link)
        if gr_link is None:
            return
        self._gr_links.pop(gr_link.uuid, None)
        gr_link.detach()
        if gr_link.scene() is self:
            self.removeItem(gr_link)

    def clear_links(self):
        """Removes all GraphicsLink items from the scene."""
        for gr_link in self.gr_links():
            self.remove_link(gr_link)

    def build_links(self, scope_node: Node):
        """Builds GraphicsLink items for the links between the drawn nodes.

        Must run after `build_nodes`: links attach to the plugs of the node items.

        Links are read from the components of the drawn plugs, so the cost depends
        only on the links touching the scope, not on the size of the stage. Every
        link is picked up once, from its source plug. Links with an end outside of
        the scope (other levels of the hierarchy) are not drawn.

        Args:
            scope_node (Node): node being drawn.
        """
        plugs = {
            plug.uuid: plug
            for gr_node in self._gr_nodes.values()
            for plug in gr_node.plugs
        }
        uuid_map = self.stage.uuid_map
        for source_uuid, source_plug in plugs.items():
            component = source_plug.component
            if not component.produces_output:
                continue
            for link_uuid in component.links_uuids:
                link = uuid_map.get(link_uuid)
                if not isinstance(link, Link) or link.source != source_uuid:
                    continue
                target_plug = plugs.get(link.target)
                if target_plug is not None:
                    self.add_link(link, source_plug, target_plug)

    def find_links_along(self, scene_points: list[QtCore.QPointF]) -> list[GraphicsLink]:
        """Find the links crossed by a polyline.

        Args:
            scene_points (list[QtCore.QPointF]): scene points of the polyline.

        Returns:
            list[GraphicsLink]: links crossed by the line.
        """
        if len(scene_points) < 2:
            return []
        line = QtGui.QPainterPath(scene_points[0])
        for point in scene_points[1:]:
            line.lineTo(point)
        # An open path has no area to intersect with, so give it some.
        stroker = QtGui.QPainterPathStroker()
        stroker.setWidth(1.0)
        area = stroker.createStroke(line)
        return [
            item
            for item in self.items(area, QtCore.Qt.ItemSelectionMode.IntersectsItemShape)
            if isinstance(item, GraphicsLink) and item.uuid in self._gr_links
        ]

    def cut_links_along(self, scene_points: list[QtCore.QPointF]) -> bool:
        """Unlink all the links crossed by a polyline in one undoable command.

        Args:
            scene_points (list[QtCore.QPointF]): scene points of the polyline.

        Returns:
            bool: at least one link was cut.
        """
        gr_links = self.find_links_along(scene_points)
        if not gr_links:
            return False
        self.stage.push_command(
            commands.UnlinkNodeComponentsCommand(
                stage=self.stage, link_uuids=[gr_link.uuid for gr_link in gr_links]
            )
        )
        return True

    @staticmethod
    def can_link(source: NodeComponent, target: NodeComponent) -> bool:
        """Check whether linking two components would be accepted.

        Args:
            source (NodeComponent): component providing output.
            target (NodeComponent): component accepting input.

        Returns:
            bool: components differ, are of the same type, can be linked in this
                direction and are not linked already.
        """
        if source is target:
            return False
        if not source.produces_output or not target.accepts_input:
            return False
        if not isinstance(target, type(source)):
            return False
        return all(link.source != source.uuid for link in target.input_links)

    # ======== Link dragging ========= #

    @property
    def is_dragging_link(self) -> bool:
        """bool: a link is being dragged from a socket."""
        return self._drag_link is not None

    def begin_link_drag(self, plug: GraphicsPlug, socket: GraphicsPlug.Socket):
        """Start dragging a link from a socket of a plug.

        Args:
            plug (GraphicsPlug): plug the drag starts at.
            socket (GraphicsPlug.Socket): socket the drag starts at.
        """
        self.cancel_link_drag()
        from_output = socket is GraphicsPlug.Socket.OUTPUT
        self._drag_origin = (plug, socket)
        self._drag_link = GraphicsLink(
            source_plug=plug if from_output else None,
            target_plug=None if from_output else plug,
        )
        anchor = plug.output_anchor() if from_output else plug.input_anchor()
        self._drag_link.set_floating_pos(anchor)
        self.addItem(self._drag_link)

    def update_link_drag(self, scene_pos: QtCore.QPointF):
        """Move the open end of the dragged link.

        Args:
            scene_pos (QtCore.QPointF): scene position of the cursor.
        """
        if self._drag_link is not None:
            self._drag_link.set_floating_pos(scene_pos)

    def cancel_link_drag(self):
        """Drop the dragged link without linking anything."""
        drag_link, self._drag_link, self._drag_origin = self._drag_link, None, None
        if drag_link is not None and drag_link.scene() is self:
            self.removeItem(drag_link)

    def finish_link_drag(self, scene_pos: QtCore.QPointF):
        """Finish dragging: link to the socket under the cursor or open the palette.

        Releasing on a socket that doesn't accept the link, or on a node, cancels
        the drag. Releasing on empty space opens the nodes palette, and the node
        created there gets linked to the socket the drag started at.

        Args:
            scene_pos (QtCore.QPointF): scene position of the release.
        """
        origin = self._drag_origin
        self.cancel_link_drag()
        if origin is None:
            return
        origin_plug, origin_socket = origin
        wanted_socket = (
            GraphicsPlug.Socket.INPUT
            if origin_socket is GraphicsPlug.Socket.OUTPUT
            else GraphicsPlug.Socket.OUTPUT
        )

        over_node = False
        for item in self.items(scene_pos):
            if isinstance(item, GraphicsPlug):
                if item.socket_at(scene_pos) is wanted_socket:
                    self._link_plugs(origin_plug, origin_socket, item)
                    return
            elif isinstance(item, GraphicsNode):
                over_node = True

        if not over_node:
            # Not inside the mouse event: the palette runs a modal event loop.
            component_uuid = origin_plug.uuid
            QtCore.QTimer.singleShot(
                0, lambda: self._open_palette_for_link(component_uuid, origin_socket)
            )

    def _link_plugs(
        self,
        origin_plug: GraphicsPlug,
        origin_socket: GraphicsPlug.Socket,
        other_plug: GraphicsPlug,
    ):
        """Link the dragged plug to the plug it was dropped on, if that is allowed.

        Args:
            origin_plug (GraphicsPlug): plug the drag started at.
            origin_socket (GraphicsPlug.Socket): socket the drag started at.
            other_plug (GraphicsPlug): plug the link was dropped on.
        """
        if origin_socket is GraphicsPlug.Socket.OUTPUT:
            source, target = origin_plug.component, other_plug.component
        else:
            source, target = other_plug.component, origin_plug.component
        self._push_link_command(source, target)

    def _push_link_command(self, source: NodeComponent, target: NodeComponent) -> bool:
        """Push a command linking two components if the link is allowed.

        Args:
            source (NodeComponent): component providing output.
            target (NodeComponent): component accepting input.

        Returns:
            bool: link was created.
        """
        if not self.can_link(source, target):
            LOGGER.debug(f"Components can't be linked: {source} -> {target}")
            return False
        try:
            self.stage.push_command(
                commands.LinkNodeComponentsCommand(
                    stage=self.stage, source=source, target=target
                )
            )
        except NyxCommandValidationError as error:
            LOGGER.warning(f"Failed to link {source} -> {target}: {error}")
            return False
        return True

    def _open_palette_for_link(self, component_uuid: UUID, socket: GraphicsPlug.Socket):
        """Show the nodes palette and link the created node to the dragged socket.

        Args:
            component_uuid (UUID): component the drag started at.
            socket (GraphicsPlug.Socket): socket the drag started at.
        """
        # Imported here: the dialog imports views that import this module.
        from nyx.editor.widgets.dialogs.popup_nodes_palette import PopupNodesPalette

        PopupNodesPalette.popup(
            on_node_spawned=lambda node: self._link_spawned_node(
                node, component_uuid, socket
            )
        )

    def _link_spawned_node(
        self, node: Node, component_uuid: UUID, socket: GraphicsPlug.Socket
    ):
        """Link the first compatible component of a new node to the dragged socket.

        Args:
            node (Node): node created by the palette.
            component_uuid (UUID): component the drag started at.
            socket (GraphicsPlug.Socket): socket the drag started at.
        """
        try:
            origin = self.stage.get_object(component_uuid)
        except StageObjectQueryError:
            return
        from_output = socket is GraphicsPlug.Socket.OUTPUT
        for component in node.components_model.list_components():
            source, target = (origin, component) if from_output else (component, origin)
            if self.can_link(source, target):
                self._push_link_command(source, target)
                return
        LOGGER.debug(f"{node.path} has no component to link to {origin}")

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
        self.cancel_link_drag()
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
