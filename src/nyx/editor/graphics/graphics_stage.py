"""
This module defines the GraphicsStage class,
which is a QGraphicsScene that manages the visual representation of
nodes and edges in the graph editor.
"""

import logging
import pathlib
import typing
from collections import deque
from uuid import UUID

import shiboken6
from PySide6 import QtCore, QtGui, QtWidgets

from nyx.core import commands
from nyx.core.exceptions import StageObjectQueryError
from nyx.core.execution_chain import ExecutionChain
from nyx.core.link import Link
from nyx.core.stage_object import StageObject
from nyx.core.stage_render_options import StageRenderOptions
from nyx.editor.graphics.background.styles import create_background
from nyx.editor.graphics.graphics_factory import create_graphics_object
from nyx.editor.graphics.graphics_link import GraphicsLink
from nyx.editor.graphics.graphics_link_drag_handler import GraphicsLinkDragHandler
from nyx.editor.graphics.graphics_node import GraphicsNode
from nyx.editor.graphics.graphics_plug import GraphicsPlug
from nyx.editor.graphics.graphics_util_object import GraphicsUtilObject
from nyx.editor.graphics.animation.link_animator import LinkAnimator, ViewArea
from nyx.editor.graphics.animation.styles import ANIMATION_CLASSES, create_animation
from nyx.core.layered_config import get_app_config
from nyx.static.enums import CoreNodeComponents, LinkAnimationStyle, StageBackGroundStyle

if typing.TYPE_CHECKING:
    from nyx.core.node import Node
    from nyx.core.node_component import NodeComponent
    from nyx.core.stage import Stage
    from nyx.core.util_object import UtilObject
    from nyx.editor.widgets.stage_graph_editor import StageGraphEditor

LOGGER = logging.getLogger(__name__)


class GraphicsStage(QtWidgets.QGraphicsScene):
    """`GraphicsStage` is a `QGraphicsScene` that manages
    the visual representation of nodes and edges in the graph editor."""

    link_drag_changed = QtCore.Signal(bool)
    """Emitted with True when a link drag starts and False when it ends."""

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
        self._gr_util_objects: dict[UUID, GraphicsUtilObject] = {}
        self._link_drag_handler = GraphicsLinkDragHandler(self)
        self._link_drag_handler.drag_changed.connect(self.link_drag_changed)
        self._link_animator = LinkAnimator(visible_areas=self._view_areas, parent=self)
        self.link_drag_changed.connect(self._link_animator.set_paused)
        self._scope_path: pathlib.PurePosixPath | None = None

        self.options = StageRenderOptions()
        # NOTE: calling self.setSceneRect(QtCore.QRect) again disables view scrolling
        self.set_scene_size(self.options.scene_width, self.options.scene_height)
        self.apply_render_options()

        self.create_connections()

    def create_connections(self):
        """Creates signal-slot connections for the graphics stage."""
        self.selectionChanged.connect(self.on_selection_changed)
        self.stage.itemChanged.connect(self.on_node_changed)
        self.stage.link_pins_changed.connect(self.on_link_pins_changed)

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

    def get_background_style(self) -> StageBackGroundStyle:
        """Get the pattern the background is drawn with.

        Returns:
            StageBackGroundStyle: style from the graphics stage config, the default one
                if the configured value is not a style.
        """
        value = get_app_config().values.editor_widgets.graphics_stage.background_style
        try:
            return StageBackGroundStyle(value)
        except ValueError:
            LOGGER.warning(
                f"Unknown background style {value!r}, "
                f"using {StageBackGroundStyle.GRID.value!r}"
            )
            return StageBackGroundStyle.GRID

    def apply_render_options(self):
        """Rebuilds the background brush and pattern from the options and config."""
        stage_config = get_app_config().values.editor_widgets.graphics_stage
        color = QtGui.QColor(stage_config.background_color)
        if color.isValid():
            self.options.background_color = color
        else:
            LOGGER.warning(
                f"Invalid background color {stage_config.background_color!r}, "
                f"using {self.options.background_color.name()!r}"
            )
        self._background = create_background(self.get_background_style(), self.options)
        self.setBackgroundBrush(self.options.background_color)
        self.update()

    def drawBackground(self, painter, rect):
        """Draws the background pattern of the scene."""
        super().drawBackground(painter, rect)
        self._background.draw(painter, rect)

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
            GraphicsNode | None: item for the node, None if the node is out of scope
                or isn't drawn.
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

        gr_node = create_graphics_object(node, node)
        if gr_node is None:
            return None
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

    # ======== Util objects ========= #

    def gr_util_objects(self) -> list[GraphicsUtilObject]:
        """Returns all items of util objects (notes, groups, ...) in the scene."""
        return list(self._gr_util_objects.values())

    def get_gr_util_object(
        self, util_object: UtilObject | UUID
    ) -> GraphicsUtilObject | None:
        """Returns the item drawn for the given util object, if there is one.

        Args:
            util_object (UtilObject | UUID): util object or its uuid.
        """
        return self._gr_util_objects.get(getattr(util_object, "uuid", util_object))

    def selected_gr_util_objects(self) -> list[GraphicsUtilObject]:
        """Returns the selected util object items in the scene."""
        return [
            item for item in self.selectedItems() if isinstance(item, GraphicsUtilObject)
        ]

    def is_selection_empty(self) -> bool:
        """Check if neither a node nor a util object is selected."""
        return self.is_gr_node_selection_empty() and not self.selected_gr_util_objects()

    def add_util_object(self, util_object: UtilObject) -> GraphicsUtilObject | None:
        """Adds the item of a util object to the scene.

        Args:
            util_object (UtilObject): util object to draw.

        Returns:
            GraphicsUtilObject | None: item for the util object, None if it isn't
                drawn.
        """
        gr_util = self._gr_util_objects.get(util_object.uuid)
        if gr_util is not None:
            if gr_util.util_object is util_object:
                return gr_util
            self.remove_util_object(util_object.uuid)

        gr_util = create_graphics_object(util_object, util_object)
        if gr_util is None:
            return None
        self._gr_util_objects[util_object.uuid] = gr_util
        self.addItem(gr_util)
        return gr_util

    def remove_util_object(self, util_object: UtilObject | UUID) -> None:
        """Removes the item of the given util object, if there is one.

        Args:
            util_object (UtilObject | UUID): util object or its uuid.
        """
        gr_util = self._gr_util_objects.pop(
            getattr(util_object, "uuid", util_object), None
        )
        if gr_util is not None:
            self.removeItem(gr_util)

    def clear_util_objects(self) -> None:
        """Removes all util object items from the scene."""
        for uuid in list(self._gr_util_objects):
            self.remove_util_object(uuid)

    def build_util_objects(self, scope_node: Node) -> None:
        """Make the util object items match the util objects of the scope node.

        Args:
            scope_node (Node): node being drawn.
        """
        util_objects = {each.uuid: each for each in scope_node.util_objects}
        for uuid, gr_util in list(self._gr_util_objects.items()):
            if util_objects.get(uuid) is not gr_util.util_object:
                self.remove_util_object(uuid)

        for uuid, util_object in util_objects.items():
            gr_util = self._gr_util_objects.get(uuid)
            if gr_util is None:
                self.add_util_object(util_object)
            else:
                gr_util.refresh()

    def commit_moves(self) -> None:
        """Push one command for all node, util object and link pin items moved."""
        stage = self.stage
        nodes, node_positions = [], []
        for gr_node in self.gr_nodes():
            if gr_node.pos() != gr_node.node.position():
                nodes.append(gr_node.node)
                node_positions.append(gr_node.pos())
        util_changes = {
            gr_util.util_object: {"position": [gr_util.pos().x(), gr_util.pos().y()]}
            for gr_util in self.gr_util_objects()
            if gr_util.pos() != gr_util.util_object.position
        }
        pin_changes = {
            gr_link.uuid: gr_link.pins
            for gr_link in self.gr_links()
            if gr_link.uuid is not None
            and gr_link.pins != stage.get_object(gr_link.uuid).pins
        }
        if not nodes and not util_changes and not pin_changes:
            return

        move_commands = []
        if nodes:
            move_commands.append(
                commands.MoveNodeCommand(
                    stage=stage, nodes=nodes, new_positions=node_positions
                )
            )
        if util_changes:
            move_commands.append(
                commands.SetUtilObjectPropertiesCommand(
                    stage, util_changes, text="Moved util objects"
                )
            )
        move_commands.extend(
            commands.SetLinkPinsCommand(stage, link_uuid, pins)
            for link_uuid, pins in pin_changes.items()
        )
        if len(move_commands) == 1:
            stage.push_command(move_commands[0])
            return

        stage.undo_stack.beginMacro("Moved items")
        try:
            stage.push_command(*move_commands)
        finally:
            stage.undo_stack.endMacro()

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
    ) -> GraphicsLink | None:
        """Adds a GraphicsLink item between two plugs.

        Args:
            link (Link): link to draw.
            source_plug (GraphicsPlug): plug the link starts at.
            target_plug (GraphicsPlug): plug the link ends at.

        Returns:
            GraphicsLink | None: new item, None if the link isn't drawn.
        """
        self.remove_link(link.uuid)
        gr_link = create_graphics_object(
            link, source_plug, target_plug, link_uuid=link.uuid, pins=link.pins
        )
        if gr_link is None:
            return None
        gr_link.attach()
        self._gr_links[link.uuid] = gr_link
        self.addItem(gr_link)
        return gr_link

    def on_link_pins_changed(self, link_uuid: UUID):
        """Show the pins a link has in the stage.

        Args:
            link_uuid (UUID): uuid of the changed link.
        """
        gr_link = self.get_gr_link(link_uuid)
        if gr_link is not None:
            gr_link.set_pins(self.stage.get_object(link_uuid).pins)

    def find_link_at(
        self, scene_pos: QtCore.QPointF, tolerance: float = 4.0
    ) -> GraphicsLink | None:
        """Find the link passing near a scene position.

        Args:
            scene_pos (QtCore.QPointF): scene position.
            tolerance (float): distance from the link in scene units.

        Returns:
            GraphicsLink | None: link closest to the position in z order, if any.
        """
        area = QtCore.QRectF(
            scene_pos.x() - tolerance,
            scene_pos.y() - tolerance,
            tolerance * 2,
            tolerance * 2,
        )
        for item in self.items(area, QtCore.Qt.ItemSelectionMode.IntersectsItemShape):
            if isinstance(item, GraphicsLink) and item.uuid in self._gr_links:
                return item
        return None

    def remove_link(self, link: GraphicsLink | Link | UUID) -> None:
        """Removes the GraphicsLink item of the given link, if there is one.

        Args:
            link (GraphicsLink | Link | UUID): item, link or link uuid.
        """
        gr_link = link if isinstance(link, GraphicsLink) else self.get_gr_link(link)
        if gr_link is None:
            return
        self._link_animator.unregister(gr_link)
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
            if not component.readable:
                continue
            for link_uuid in component.links_uuids:
                link = uuid_map.get(link_uuid)
                if not isinstance(link, Link) or link.source != source_uuid:
                    continue
                target_plug = plugs.get(link.target)
                if target_plug is not None:
                    self.add_link(link, source_plug, target_plug)

    @property
    def link_animator(self) -> LinkAnimator:
        """LinkAnimator: animator of the link animations, such as the chain pulses."""
        return self._link_animator

    @classmethod
    def is_flow_chain_highlight_enabled(cls) -> bool:
        """Check whether links on the execution chain are animated.

        Returns:
            bool: enabled in the graphics stage config.
        """
        return get_app_config().values.editor_widgets.graphics_stage.highlight_flow_chain

    @classmethod
    def get_flow_chain_highlight_style(cls) -> LinkAnimationStyle:
        """Get the animation that highlights the execution chain.

        Returns:
            LinkAnimationStyle: style from the graphics stage config, the default one
                if the configured value is not a style.
        """
        stage_config = get_app_config().values.editor_widgets.graphics_stage
        value = stage_config.highlight_flow_chain_style
        try:
            return LinkAnimationStyle(value)
        except ValueError:
            LOGGER.warning(
                f"Unknown flow chain highlight style {value!r}, "
                f"using {LinkAnimationStyle.PULSE.value!r}"
            )
            return LinkAnimationStyle.PULSE

    def update_flow_chain_highlight(self, scope_node: Node):
        """Highlight the flow links on the execution chain of the scope.

        Nothing is resolved or animated when the highlight is disabled. Must run after
        `build_links`.

        Args:
            scope_node (Node): node being drawn.
        """
        for animation_class in ANIMATION_CLASSES.values():
            self._link_animator.clear(animation_class)
        if not self.is_flow_chain_highlight_enabled():
            return

        style = self.get_flow_chain_highlight_style()
        chain = ExecutionChain.find_node_uuids(scope_node)
        for gr_link in self.gr_links():
            if self._is_flow_link_on_chain(gr_link, chain):
                self._link_animator.register(gr_link, create_animation(style))

    @staticmethod
    def _is_flow_link_on_chain(gr_link: GraphicsLink, chain: frozenset[UUID]) -> bool:
        """Check whether a link is an active flow link leaving an active chain node.

        Args:
            gr_link (GraphicsLink): link to check.
            chain (frozenset[UUID]): uuids of the nodes on the chain.

        Returns:
            bool: the link is a flow link of an active component and its source node
                is active and on the chain. The pulse stops at an inactive node.
        """
        source = gr_link.source_plug.component
        return (
            source.get_type_id() == CoreNodeComponents.FLOW
            and source.is_active
            and source.node.is_active()
            and source.node.uuid in chain
        )

    def _view_areas(self) -> list[ViewArea]:
        """Get the parts of the scene that visible views show.

        Returns:
            list[ViewArea]: area and scale of every visible view.
        """
        return [
            ViewArea(
                view.mapToScene(view.viewport().rect()).boundingRect(),
                view.transform().m11(),
            )
            for view in self.views()
            if view.isVisible()
        ]

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
                direction, don't make nodes depend on each other and are not linked
                already.
        """
        if source is target:
            return False
        if source.node.is_in_locked_scope or target.node.is_in_locked_scope:
            return False
        if not source.readable or not target.writable:
            return False
        if not target.datatype.accepts(source.datatype):
            return False
        if source.stage.would_link_create_cycle(source, target):
            return False
        return all(link.source != source.uuid for link in target.input_links)

    # ======== Link dragging ========= #

    @property
    def link_drag_handler(self) -> GraphicsLinkDragHandler:
        """GraphicsLinkDragHandler: object handling dragging of links from sockets."""
        return self._link_drag_handler

    @property
    def is_dragging_link(self) -> bool:
        """bool: a link is being dragged from a socket."""
        return self._link_drag_handler.is_dragging

    def begin_link_drag(self, plug: GraphicsPlug, socket: GraphicsPlug.Socket):
        """Start dragging a link from a socket of a plug.

        Args:
            plug (GraphicsPlug): plug the drag starts at.
            socket (GraphicsPlug.Socket): socket the drag starts at.
        """
        self._link_drag_handler.begin(plug, socket)

    def update_link_drag(self, scene_pos: QtCore.QPointF):
        """Move the open end of the dragged link.

        Args:
            scene_pos (QtCore.QPointF): scene position of the cursor.
        """
        self._link_drag_handler.update(scene_pos)

    def finish_link_drag(self, scene_pos: QtCore.QPointF):
        """Drop the dragged link at a scene position.

        Args:
            scene_pos (QtCore.QPointF): scene position of the release.
        """
        self._link_drag_handler.finish(scene_pos)

    def cancel_link_drag(self):
        """Drop the dragged link without linking anything."""
        self._link_drag_handler.cancel()

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
        previous_util_selection = [gr.uuid for gr in self.selected_gr_util_objects()]
        self.cancel_link_drag()
        self.clear_links()
        if scope_path != self._scope_path:
            self.clear_nodes()
            self.clear_util_objects()
            self._scope_path = scope_path
        scope_node = self.stage.get_object(scope_path)
        self.build_nodes(scope_node)
        self.build_util_objects(scope_node)
        self.build_links(scope_node)
        self.update_flow_chain_highlight(scope_node)
        self._restore_selection(previous_selection)
        for uuid in previous_util_selection:
            gr_util = self._gr_util_objects.get(uuid)
            if gr_util is not None:
                gr_util.setSelected(True)

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
            for gr_node in list(self.selected_gr_nodes()):
                gr_node.setSelected(False)
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
        """Updates the selection model to match the scene selection.

        The model reports the change once, however many nodes are selected. Nothing is
        done while a rubber band is being dragged: the scene selection changes for every
        node that enters the band, so the view syncs it when the band is released.
        """
        view = self.graph_editor.gr_view
        if view is not None and view.is_rubber_banding:
            return
        selection = QtCore.QItemSelection()
        for gr_node in self.selected_gr_nodes():
            index = gr_node.node.index()
            selection.select(index, index)
        self.selection_model.select(
            selection, QtCore.QItemSelectionModel.SelectionFlag.ClearAndSelect
        )

    def start_selected_node_rename(self):
        """Starts editing the title of the last selected GraphicsNode item."""
        gr_node = self.get_last_selected_gr_node()
        if not gr_node:
            return
        gr_node.title_item.edit()
