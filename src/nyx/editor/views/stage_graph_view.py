import enum
import logging
import functools
import math
import typing

# import pathlib
from PySide6 import QtCore, QtGui, QtWidgets

from nyx.core import commands
from nyx.editor.core.action_router import ACTION_ROUTER
from nyx.editor.core.actions import ActionId
from nyx.editor.graphics.graphics_cutline import GraphCutLine
from nyx.editor.graphics.graphics_node import GraphicsNode
from nyx.editor.utils import clipboard, context_menus
from nyx.static.vars import NODE_TYPE_MIME

if typing.TYPE_CHECKING:
    from nyx.core import Node
    from nyx.editor.graphics.graphics_stage import GraphicsStage
    from nyx.editor.widgets.stage_graph_editor import StageGraphEditor


LOGGER = logging.getLogger(__name__)


class StageGraphView(QtWidgets.QGraphicsView):
    """Graphics view of a stage scope with zoom, panning and node drops.

    Attributes:
        item_drag_entered: emitted when an unhandled drag enters the view
        item_dropped: emitted when an unhandled drop happens on the view
    """

    # Signals
    item_drag_entered = QtCore.Signal(QtGui.QDragEnterEvent)
    item_dropped = QtCore.Signal(QtGui.QDropEvent)

    # Constants
    EDGE_DRAG_START_THRESHOLD = 50
    HIGH_QUALITY_ZOOM = 4
    DEFAULT_ZOOM = 10  # zoom level at 100% scale
    FOCUS_MARGIN = 40  # scene units kept around nodes when fitting

    class InteractionMode(enum.Enum):
        """Mouse interaction modes of the view."""

        NOOP = enum.auto()
        EDGE_DRAG = enum.auto()
        EDGE_CUT = enum.auto()

    def __init__(
        self, graph_editor: StageGraphEditor, parent: QtWidgets.QWidget | None = None
    ) -> None:
        """Initialize StageGraphView.

        Args:
            graph_editor (StageGraphEditor): editor owning the view.
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(graph_editor.gr_stage, parent=parent)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.graph_editor: StageGraphEditor = graph_editor
        self._interaction_mode = StageGraphView.InteractionMode.NOOP
        self.cutline = GraphCutLine()
        self.scene().addItem(self.cutline)

        # Zoom
        self.zoom_in_factor = 1.25
        self.zoom_clamp = True
        self.zoom = self.DEFAULT_ZOOM
        self.zoom_step = 1
        self.zoom_range = (-5.0, 10.0)
        # Positions
        self.last_lmb_click_pos = QtCore.QPointF(0.0, 0.0)
        self.last_scene_mouse_pos = QtCore.QPointF(0.0, 0.0)
        # Toggles
        self.rubberband_dragging_rect = False

        self._setup_view()
        self.update_render_hints()
        self.create_actions()
        self.create_widgets()
        self.create_layouts()
        self.create_connections()

    def _setup_view(self):
        """Configure view flags, scrollbars and drag mode."""
        self.setInteractive(True)
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
        self.setAcceptDrops(True)

    def get_view_state(self) -> dict:
        """Zoom level and the scene point at the viewport center."""
        center = self.mapToScene(self.viewport().rect().center())
        return {"zoom": self.zoom, "center": [center.x(), center.y()]}

    def apply_view_state(self, state: dict) -> None:
        """Restore zoom and center from saved state.

        Args:
            state (dict): state from `get_view_state`. The zoom is clamped to the zoom
                range.
        """
        zoom = float(state.get("zoom", self.DEFAULT_ZOOM))
        zoom = max(self.zoom_range[0], min(self.zoom_range[1], zoom))
        scale = self.zoom_in_factor ** (zoom - self.DEFAULT_ZOOM)
        self.zoom = zoom
        self.setTransform(QtGui.QTransform.fromScale(scale, scale))
        x, y = state.get("center", [0.0, 0.0])
        self.centerOn(float(x), float(y))
        self.update_render_hints()

    def update_render_hints(self):
        """Enable text antialiasing only at higher zoom levels."""
        if self.zoom > self.HIGH_QUALITY_ZOOM:
            self.setRenderHints(
                QtGui.QPainter.RenderHint.Antialiasing
                | QtGui.QPainter.RenderHint.TextAntialiasing
                | QtGui.QPainter.RenderHint.SmoothPixmapTransform
            )
        else:
            self.setRenderHints(
                QtGui.QPainter.RenderHint.Antialiasing
                | QtGui.QPainter.RenderHint.SmoothPixmapTransform
            )

    def create_actions(self):
        """Register handlers of the editing actions for this view."""

        def has_selection():
            """bool: at least one node is selected."""
            return not self.gr_stage.is_gr_node_selection_empty()

        register = functools.partial(ACTION_ROUTER.register_handler, scope=self)
        register(ActionId.CREATE_NODE, self.create_new_node)
        register(ActionId.PASTE, self.paste_nodes_from_clipboard)
        register(ActionId.COPY, self.copy_selected_nodes, enabled_fn=has_selection)
        register(ActionId.CUT, self.cut_selected_nodes, enabled_fn=has_selection)
        register(ActionId.DELETE, self.delete_selected, enabled_fn=has_selection)
        register(ActionId.DELETE_NODE, self.delete_selected, enabled_fn=has_selection)
        register(
            ActionId.COPY_NODE_PATH,
            self.copy_selected_node_path,
            enabled_fn=has_selection,
        )
        register(
            ActionId.FOCUS_SELECTED,
            self.focus_on_selected_nodes,
            enabled_fn=has_selection,
        )

    def create_widgets(self):
        """Create widgets. The view has none."""
        pass

    def create_layouts(self):
        """Create layouts. The view has none."""
        pass

    def create_connections(self):
        """Connect signals."""
        self.customContextMenuRequested.connect(self.show_context_menu)

    def update_actions(self):
        """Refresh the enabled state of the actions."""
        ACTION_ROUTER.refresh_enabled()

    @property
    def stage(self):
        """Stage: stage of the owning editor."""
        return self.graph_editor.stage

    @property
    def is_dragging(self):
        """bool: view is being panned."""
        return not self.isInteractive()

    @property
    def interaction_mode(self):
        """StageGraphView.InteractionMode: current mouse interaction mode."""
        return self._interaction_mode

    @property
    def gr_stage(self) -> GraphicsStage:
        """GraphicsStage: scene shown by the view."""
        return self.scene()

    def set_interaction_mode(self, mode: StageGraphView.InteractionMode):
        """Set the mouse interaction mode.

        Args:
            mode (StageGraphView.InteractionMode): new mode.
        """
        self._interaction_mode = mode
        LOGGER.debug(f"Interaction mode: {mode}")

    def get_center_position(self) -> QtCore.QPointF:
        """QtCore.QPointF: scene point at the center of the viewport."""
        return self.mapToScene(self.viewport().rect().center())

    # Mouse
    def wheelEvent(self, event: QtGui.QWheelEvent):
        """Zoom in or out around the cursor, within the zoom range.

        Args:
            event (QtGui.QWheelEvent): event.
        """
        zoom_out_factor = 1.0 / self.zoom_in_factor

        if event.angleDelta().y() > 0:
            zoom_factor = self.zoom_in_factor
            self.zoom += self.zoom_step
        else:
            zoom_factor = zoom_out_factor
            self.zoom -= self.zoom_step

        clamped = False
        if self.zoom < self.zoom_range[0]:
            self.zoom, clamped = self.zoom_range[0], True
        if self.zoom > self.zoom_range[1]:
            self.zoom, clamped = self.zoom_range[1], True

        # Set actual scale
        if not clamped or not self.zoom_clamp:
            self.scale(zoom_factor, zoom_factor)
            # self.update_edge_width()
            self.update_render_hints()

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        """Enter the scope of a double clicked node.

        Args:
            event (QtGui.QMouseEvent): event.
        """
        gr_item = self.itemAt(event.pos())
        if not gr_item:
            event.ignore()
            return
        elif isinstance(gr_item, GraphicsNode):
            self.graph_editor.set_scope_path(gr_item.node.path)
            event.accept()
            return
        else:
            super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        """Dispatch to the handler of the pressed button.

        Args:
            event (QtGui.QMouseEvent): event.
        """
        if event.button() == QtCore.Qt.MiddleButton:
            self.middle_mouse_press(event)
        elif event.button() == QtCore.Qt.LeftButton:
            self.left_mouse_press(event)
        elif event.button() == QtCore.Qt.RightButton:
            self.right_mouse_press(event)
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        """Dispatch to the handler of the released button.

        Args:
            event (QtGui.QMouseEvent): event.
        """
        if event.button() == QtCore.Qt.MiddleButton:
            self.middle_mouse_release(event)
        elif event.button() == QtCore.Qt.LeftButton:
            self.left_mouse_release(event)
        elif event.button() == QtCore.Qt.RightButton:
            self.right_mouse_release(event)
        else:
            super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        """Extend the cutline while cutting links.

        Args:
            event (QtGui.QMouseEvent): event.
        """
        scene_pos = self.mapToScene(event.pos())
        # self.is_view_dragging = not self.isInteractive()

        try:
            # if self.edge_mode == StageGraphView.EdgeMode.DRAG:
            #     pos = scene_pos
            #     pos.setX(pos.x() - 1.0)
            #     # self.dragging.update_positions(pos.x(), pos.y())
            pass

            if self.interaction_mode is self.InteractionMode.EDGE_CUT and self.cutline:
                self.cutline.line_points.append(scene_pos)
                self.cutline.update()

        except Exception:
            LOGGER.exception("mouseMoveEvent exception")

        self.last_scene_mouse_pos = scene_pos
        super().mouseMoveEvent(event)

    def left_mouse_press(self, event: QtGui.QMouseEvent):
        """Handle left button press.

        Args:
            event (QtGui.QMouseEvent): event.
        """
        item = self.get_item_at_click(event)
        # Store click position for future use
        self.last_lmb_click_pos = self.mapToScene(event.pos())

        # Handle socket click
        # if isinstance(item, graphics_socket.QLGraphicsSocket):
        #     if self.edge_mode == QLGraphicsView.EdgeMode.NOOP:
        #         self.edge_mode = QLGraphicsView.EdgeMode.DRAG
        #         self.dragging.start_edge_drag(item)
        #         return

        # if self.edge_mode == QLGraphicsView.EdgeMode.DRAG:
        #     result = self.dragging.end_edge_drag(item)
        #     if result:
        #         return

        if not item:
            if event.modifiers() & QtCore.Qt.ControlModifier:
                self.set_interaction_mode(self.InteractionMode.EDGE_CUT)
                fake_event = QtGui.QMouseEvent(
                    QtCore.QEvent.MouseButtonRelease,
                    event.localPos(),
                    event.screenPos(),
                    QtCore.Qt.LeftButton,
                    QtCore.Qt.NoButton,
                    event.modifiers(),
                )
                super().mouseReleaseEvent(fake_event)
                event.ignore()
                return
            else:
                if not self.is_dragging:
                    self.gr_stage.selection_model.clearSelection()
                self.rubberband_dragging_rect = True

        super().mousePressEvent(event)

    def left_mouse_release(self, event: QtGui.QMouseEvent):
        """Handle left button release, finishing link cutting if active.

        Args:
            event (QtGui.QMouseEvent): event.
        """
        # item = self.get_item_at_click(event)
        try:
            # if self.edge_mode == QLGraphicsView.EdgeMode.DRAG:
            #     if self.check_lmb_release_delta(event):
            #         result = self.dragging.end_edge_drag(item)
            #         if result:
            #             return

            if self.interaction_mode == self.InteractionMode.EDGE_CUT:
                self.cut_intersecting_edges()
                self.cutline.line_points = []
                self.cutline.update()
                self.set_interaction_mode(self.InteractionMode.NOOP)
                event.accept()
                return

            if self.rubberband_dragging_rect:
                self.rubberband_dragging_rect = False
                self.gr_stage.on_selection_changed()
                event.accept()
                return
        except Exception:
            LOGGER.exception("Left mouse release exception")

        super().mouseReleaseEvent(event)

    # Right mouse
    def right_mouse_press(self, event: QtGui.QMouseEvent):
        """Accept the right button press so the context menu can open.

        Args:
            event (QtGui.QMouseEvent): event.
        """
        event.accept()

    def right_mouse_release(self, event: QtGui.QMouseEvent):
        """Handle right button release.

        Args:
            event (QtGui.QMouseEvent): event.
        """
        super().mouseReleaseEvent(event)

    def get_item_at_click(
        self, event: QtGui.QMouseEvent
    ) -> QtWidgets.QGraphicsItem | None:
        """Object at click event position"""
        item = self.itemAt(event.pos())
        return item

    # Middle mouse
    def middle_mouse_press(self, event: QtGui.QMouseEvent):
        """Start panning the view with the middle button.

        Args:
            event (QtGui.QMouseEvent): event.
        """
        release_event = QtGui.QMouseEvent(
            QtCore.QEvent.MouseButtonRelease,
            event.localPos(),
            event.screenPos(),
            QtCore.Qt.LeftButton,
            QtCore.Qt.NoButton,
            event.modifiers(),
        )
        super().mouseReleaseEvent(release_event)
        self.setInteractive(False)
        self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
        fake_event = QtGui.QMouseEvent(
            event.type(),
            event.localPos(),
            event.screenPos(),
            QtCore.Qt.LeftButton,
            event.buttons() | QtCore.Qt.LeftButton,
            event.modifiers(),
        )
        super().mousePressEvent(fake_event)

    def middle_mouse_release(self, event: QtGui.QMouseEvent):
        """Stop panning and restore selection mode.

        Args:
            event (QtGui.QMouseEvent): event.
        """
        fake_event = QtGui.QMouseEvent(
            event.type(),
            event.localPos(),
            event.screenPos(),
            QtGui.Qt.LeftButton,
            event.buttons() & ~QtGui.Qt.LeftButton,
            event.modifiers(),
        )
        super().mouseReleaseEvent(fake_event)
        self.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
        self.setInteractive(True)

    # Dragging
    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> bool:
        """Accept node type drags, forward others.

        Args:
            event (QtGui.QDragEnterEvent): event.
        """
        if self._is_node_type_drag(event):
            event.acceptProposedAction()
            return
        self.item_drag_entered.emit(event)

    def dragMoveEvent(self, event: QtGui.QDragMoveEvent):
        """Accept node type drags.

        Args:
            event (QtGui.QDragMoveEvent): event.
        """
        if self._is_node_type_drag(event):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event: QtGui.QDropEvent):
        """Request a node of the dropped type at the drop position.

        Args:
            event (QtGui.QDropEvent): event.
        """
        if self._is_node_type_drag(event):
            type_id: str = bytes(event.mimeData().data(NODE_TYPE_MIME)).decode()
            scene_position = self.mapToScene(event.position().toPoint())
            self.graph_editor.node_type_dropped.emit(type_id, scene_position)
            event.acceptProposedAction()
            return
        self.item_dropped.emit(event)

    @staticmethod
    def _is_node_type_drag(event: QtGui.QDragEnterEvent):
        """Check whether a drag carries a node type.

        Args:
            event (QtGui.QDragEnterEvent): drag event.

        Returns:
            bool: drag holds a node type.
        """
        return event.mimeData().hasFormat(NODE_TYPE_MIME)

    def show_context_menu(self, point: QtCore.QPoint):
        """Show the nodes context menu.

        Args:
            point (QtCore.QPoint): position in view coordinates.
        """
        self.update_actions()
        menu = context_menus.build_nodes_context_menu(
            self, has_selection=not self.gr_stage.is_gr_node_selection_empty()
        )
        menu.exec_(self.mapToGlobal(point))

    def cut_intersecting_edges(self):
        """Cut links crossed by the cutline. Not implemented yet."""
        cut_result = False
        # for ix in range(len(self.cutline.line_points) - 1):
        #     pt1 = self.cutline.line_points[ix]
        #     pt2 = self.cutline.line_points[ix + 1]

        # TODO: Should be optimized as gets slow with large scenes
        # for edge in self.scene.edges[:]:
        #     if edge.gr_edge.intersects_with(pt1, pt2):
        #         edge.remove()
        #         cut_result = True
        if cut_result:
            # TODO: Disconnect plugs here
            pass
            # self.scene.history.store_history('Edges cut', set_modified=True)

    def create_new_node(self):
        """Show the nodes palette at the last mouse position."""
        self.graph_editor.show_nodes_palette_centered(self.last_scene_mouse_pos)

    def delete_selected(self):
        """Delete the selected nodes through an undoable command."""
        if not self.stage:
            return

        if self.gr_stage.is_gr_node_selection_empty():
            LOGGER.warning("No nodes selected to delete!")
            return

        selected_gr_nodes = self.scene().selected_gr_nodes()
        nodes_to_delete: list[Node] = [gr_node.node for gr_node in selected_gr_nodes]
        del_cmd = commands.DeleteNodeCommand(stage=self.stage, nodes=nodes_to_delete)
        self.stage.push_command(del_cmd)
        self.scene().rebuild_current_scope()

    def copy_selected_nodes(self):
        """Copy the selected nodes to the clipboard."""
        selected_nodes = [gr_node.node for gr_node in self.gr_stage.selected_gr_nodes()]
        if not selected_nodes:
            return

        clipboard.serialize_nodes_to_clipboard(selected_nodes, delete=False)
        LOGGER.info("Copied selected nodes")

    def cut_selected_nodes(self):
        """Cut the selected nodes to the clipboard."""
        selected_nodes = [gr_node.node for gr_node in self.gr_stage.selected_gr_nodes()]
        if not selected_nodes:
            return

        clipboard.serialize_nodes_to_clipboard(selected_nodes, delete=True)
        LOGGER.info("Cut selected nodes")

    def paste_nodes_from_clipboard(self):
        """Paste nodes from the clipboard into the current scope."""
        serialized_nodes = clipboard.get_serialized_nodes_from_clipboard()
        if not serialized_nodes:
            LOGGER.warning("No nodes found in the clipboard!")
            return

        parent_node = self.stage.get_object(self.graph_editor.get_scope_path())
        position = self.last_scene_mouse_pos
        paste_cmd = commands.PasteNodesCommand(
            stage=self.stage,
            serialize_nodes=serialized_nodes,
            position=position,
            parent_node=parent_node,
        )
        self.stage.push_command(paste_cmd)

    def copy_selected_node_path(self):
        """Copy the path of the last selected node to the clipboard."""
        gr_node = self.gr_stage.get_last_selected_gr_node()
        if gr_node is None:
            return
        path = gr_node.node.path.as_posix()
        QtWidgets.QApplication.clipboard().setText(path)
        LOGGER.info(f"Copied node path: {path}")

    def focus_on_selected_nodes(self):
        """Center on the selected nodes, zooming so they fit in the view."""
        selected_nodes = self.gr_stage.graph_editor.list_selected_nodes()
        nodes_in_scope = self.gr_stage.graph_editor.filter_nodes_by_scope(selected_nodes)

        nodes_rect = QtCore.QRectF()
        for node in nodes_in_scope:
            if node.gr_node is not None:
                nodes_rect = nodes_rect.united(node.gr_node.sceneBoundingRect())

        if nodes_rect.isNull():
            return
        self.fit_scene_rect(nodes_rect)

    def fit_scene_rect(self, scene_rect: QtCore.QRectF) -> None:
        """Center on `scene_rect` and zoom to fit it (plus margin) in the viewport.

        The zoom level stays within `zoom_range` when `zoom_clamp` is enabled, so
        a small rect is never magnified beyond the maximum zoom.
        """
        margin = self.FOCUS_MARGIN
        padded_rect = scene_rect.adjusted(-margin, -margin, margin, margin)
        viewport_rect = self.viewport().rect()
        if viewport_rect.isEmpty():
            self.centerOn(padded_rect.center())
            return

        fit_scale = min(
            viewport_rect.width() / padded_rect.width(),
            viewport_rect.height() / padded_rect.height(),
        )
        zoom = self.DEFAULT_ZOOM + math.log(fit_scale, self.zoom_in_factor)
        if self.zoom_clamp:
            zoom = max(self.zoom_range[0], min(self.zoom_range[1], zoom))

        scale = self.zoom_in_factor ** (zoom - self.DEFAULT_ZOOM)
        self.zoom = zoom
        self.setTransform(QtGui.QTransform.fromScale(scale, scale))
        self.centerOn(padded_rect.center())
        self.update_render_hints()
