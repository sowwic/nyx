import dataclasses
import enum
import logging
import time
import typing

# import pathlib
from PySide6 import QtCore, QtGui, QtWidgets

from nyx.editor.core.action_condition import CallableCondition
from nyx.editor.core.action_router import ACTION_ROUTER
from nyx.editor.graphics.graphics_cutline import GraphCutLine
from nyx.editor.graphics.graphics_node import GraphicsNode
from nyx.editor.utils import context_menus
from nyx.editor.views.stage_graph_actions import StageGraphActions
from nyx.editor.views.stage_graph_zoom import StageGraphZoom
from nyx.static.vars import NODE_TYPE_MIME

if typing.TYPE_CHECKING:
    from nyx.editor.graphics.graphics_stage import GraphicsStage
    from nyx.editor.views.stage_graph_debug_overlay import StageGraphDebugOverlay
    from nyx.editor.widgets.stage_graph_editor import StageGraphEditor


LOGGER = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class StageGraphViewState:
    """Snapshot of the state of the view that decides what the user may do.

    Attributes:
        is_idle: no mouse interaction (link drag, link cut) is running.
        has_selection: at least one node is selected.
    """

    is_idle: bool
    has_selection: bool

    @property
    def can_edit_selection(self) -> bool:
        """bool: the selected nodes can be copied, deleted, focused, ..."""
        return self.is_idle and self.has_selection


class StageGraphView(QtWidgets.QGraphicsView):
    """Graphics view of a stage scope with zoom, panning and node drops.

    Attributes:
        item_drag_entered: emitted when an unhandled drag enters the view
        item_dropped: emitted when an unhandled drop happens on the view
    """

    # Signals
    item_drag_entered = QtCore.Signal(QtGui.QDragEnterEvent)
    item_dropped = QtCore.Signal(QtGui.QDropEvent)
    state_changed = QtCore.Signal()
    """Emitted when the interaction mode or the selection changed."""

    # Constants
    HIGH_QUALITY_ZOOM = StageGraphZoom.HIGH_QUALITY_ZOOM
    DEFAULT_ZOOM = StageGraphZoom.DEFAULT_ZOOM
    FOCUS_MARGIN = 40  # scene units kept around nodes when fitting

    class InteractionMode(enum.Enum):
        """Mouse interaction modes of the view."""

        NOOP = enum.auto()
        LINK_DRAG = enum.auto()
        LINK_CUT = enum.auto()
        RUBBER_BAND = enum.auto()

    def __init__(
        self, graph_editor: StageGraphEditor, parent: QtWidgets.QWidget | None = None
    ) -> None:
        """Initialize StageGraphView
        Args:
            graph_editor (StageGraphEditor): editor owning the view.
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(graph_editor.gr_stage, parent=parent)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.graph_editor: StageGraphEditor = graph_editor
        self._interaction_mode = StageGraphView.InteractionMode.NOOP
        self._undo_suspended = False
        self._create_conditions()
        self.edit_actions = StageGraphActions(self)
        self.debug_overlay: StageGraphDebugOverlay | None = None
        self.cutline = GraphCutLine()
        self.scene().addItem(self.cutline)

        # Zoom
        self.zoom_controller = StageGraphZoom()
        # Positions
        self.last_lmb_click_pos = QtCore.QPointF(0.0, 0.0)
        self.last_scene_mouse_pos = QtCore.QPointF(0.0, 0.0)

        self._setup_view()
        self.update_render_hints()
        self.create_actions()
        self.create_connections()

    def _setup_view(self):
        """Configure view flags, scrollbars and drag mode."""
        self.setInteractive(True)
        self.setViewportUpdateMode(
            QtWidgets.QGraphicsView.ViewportUpdateMode.FullViewportUpdate
        )
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
        self.setAcceptDrops(True)

    @property
    def zoom(self) -> float:
        """float: current zoom level."""
        return self.zoom_controller.zoom

    @zoom.setter
    def zoom(self, value: float):
        self.zoom_controller.zoom = value

    @property
    def zoom_range(self) -> tuple[float, float]:
        """tuple[float, float]: lowest and highest zoom level."""
        return self.zoom_controller.zoom_range

    @property
    def zoom_in_factor(self) -> float:
        """float: scale factor of one zoom step."""
        return self.zoom_controller.zoom_in_factor

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
        self.zoom_controller.set_zoom(float(state.get("zoom", self.DEFAULT_ZOOM)))
        self.setTransform(self.zoom_controller.transform)
        x, y = state.get("center", [0.0, 0.0])
        self.centerOn(float(x), float(y))
        self.update_render_hints()

    def update_render_hints(self):
        """Enable text antialiasing only at higher zoom levels."""
        if self.zoom_controller.wants_text_antialiasing:
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
        self.edit_actions.register()

    def _create_conditions(self):
        """Create the conditions of the actions, following `state_changed`."""
        self.idle_condition = CallableCondition(
            lambda: self.get_current_state().is_idle,
            self.state_changed,
            description="no mouse interaction is running",
        )
        self.has_selection_condition = CallableCondition(
            lambda: self.get_current_state().has_selection,
            self.state_changed,
            description="nodes are selected",
        )
        self.selection_editable_condition = (
            self.idle_condition & self.has_selection_condition
        )

    def get_current_state(self) -> StageGraphViewState:
        """StageGraphViewState: what the view currently allows."""
        return StageGraphViewState(
            is_idle=self.is_idle,
            has_selection=not self.gr_stage.is_gr_node_selection_empty(),
        )

    def create_connections(self):
        """Connect signals."""
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.gr_stage.link_drag_changed.connect(self._on_link_drag_changed)

    @property
    def stage(self):
        """Stage: stage of the owning editor."""
        return self.graph_editor.stage

    @property
    def is_dragging(self):
        """bool: view is being panned."""
        return not self.isInteractive()

    @property
    def is_idle(self) -> bool:
        """bool: no mouse interaction (link drag, link cut) is running."""
        return self._interaction_mode is StageGraphView.InteractionMode.NOOP

    @property
    def is_rubber_banding(self) -> bool:
        """bool: a rubber band selection is being dragged."""
        return self._interaction_mode is StageGraphView.InteractionMode.RUBBER_BAND

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
        # Actions follow the mode through their conditions.
        self.state_changed.emit()
        self._set_undo_available(self.is_idle)

    def _set_undo_available(self, available: bool):
        """Turn undo and redo off while a mouse interaction is running.

        The undo and redo actions follow the active stack of the undo group of the
        main window, so the stack of the stage is taken out of the group.

        Args:
            available (bool): undo and redo can be used.
        """
        main_window = getattr(QtWidgets.QApplication.instance(), "main_window", None)
        if main_window is None:
            return
        undo_group = main_window().undo_group
        undo_stack = self.stage.undo_stack
        if not available:
            if undo_group.activeStack() is undo_stack:
                undo_group.setActiveStack(None)
                self._undo_suspended = True
            return

        if not self._undo_suspended:
            return
        self._undo_suspended = False
        # Another stage may have been activated meanwhile, don't take it over.
        if undo_group.activeStack() is None:
            undo_group.setActiveStack(undo_stack)

    def _on_link_drag_changed(self, is_dragging: bool):
        """Follow link dragging done by the plugs of the scene.

        Args:
            is_dragging (bool): a link drag started (True) or ended (False).
        """
        if is_dragging:
            self.set_interaction_mode(self.InteractionMode.LINK_DRAG)
        elif self.interaction_mode is self.InteractionMode.LINK_DRAG:
            self.set_interaction_mode(self.InteractionMode.NOOP)

    def get_center_position(self) -> QtCore.QPointF:
        """QtCore.QPointF: scene point at the center of the viewport."""
        return self.mapToScene(self.viewport().rect().center())

    def paintEvent(self, event: QtGui.QPaintEvent):
        """Paint the scene, then the debug overlay if it is on.

        Args:
            event (QtGui.QPaintEvent): event.
        """
        overlay = self.debug_overlay
        started = time.perf_counter()
        super().paintEvent(event)
        if overlay is None:
            return
        overlay.record_paint(time.perf_counter() - started)
        painter = QtGui.QPainter(self.viewport())
        overlay.paint(painter)
        painter.end()

    # Mouse
    def wheelEvent(self, event: QtGui.QWheelEvent):
        """Zoom in or out around the cursor, within the zoom range.

        Args:
            event (QtGui.QWheelEvent): event.
        """
        zoom_factor = self.zoom_controller.step(event.angleDelta().y() > 0)
        if zoom_factor is not None:
            self.scale(zoom_factor, zoom_factor)
            self.update_render_hints()

    @staticmethod
    def _owning_gr_node(gr_item: QtWidgets.QGraphicsItem) -> GraphicsNode | None:
        """Find the node item that `gr_item` is, or is a child of (title, plug, ...).

        Args:
            gr_item (QtWidgets.QGraphicsItem): item under the cursor.

        Returns:
            GraphicsNode | None: owning node item, if any.
        """
        while gr_item is not None and not isinstance(gr_item, GraphicsNode):
            gr_item = gr_item.parentItem()
        return gr_item

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        """Enter the scope of a double clicked node.

        Args:
            event (QtGui.QMouseEvent): event.
        """
        gr_item = self.itemAt(event.position().toPoint())
        if not gr_item:
            event.ignore()
            return
        gr_node = self._owning_gr_node(gr_item)
        if gr_node is not None:
            self.graph_editor.set_scope_path(gr_node.node.path)
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
        scene_pos = self.mapToScene(event.position().toPoint())

        try:
            if self.interaction_mode is self.InteractionMode.LINK_CUT and self.cutline:
                self.cutline.add_point(scene_pos)
        except Exception:
            LOGGER.exception("mouseMoveEvent exception")

        self.last_scene_mouse_pos = scene_pos
        super().mouseMoveEvent(event)

    def left_mouse_press(self, event: QtGui.QMouseEvent):
        """Handle left button press.

        Args:
            event (QtGui.QMouseEvent): event.
        """
        item = self.itemAt(event.position().toPoint())
        # A band whose release never came must not hold back the selection.
        if self.interaction_mode is self.InteractionMode.RUBBER_BAND:
            self.set_interaction_mode(self.InteractionMode.NOOP)
        # Store click position for future use
        self.last_lmb_click_pos = self.mapToScene(event.position().toPoint())

        if not item:
            if event.modifiers() & QtCore.Qt.ControlModifier:
                self.set_interaction_mode(self.InteractionMode.LINK_CUT)
                fake_event = QtGui.QMouseEvent(
                    QtCore.QEvent.MouseButtonRelease,
                    event.position(),
                    event.globalPosition(),
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
                self.set_interaction_mode(self.InteractionMode.RUBBER_BAND)

        super().mousePressEvent(event)

    def left_mouse_release(self, event: QtGui.QMouseEvent):
        """Handle left button release, finishing link cutting if active.

        Args:
            event (QtGui.QMouseEvent): event.
        """
        try:
            if self.interaction_mode == self.InteractionMode.LINK_CUT:
                # Back to idle first: undo is off until then and the cut is a command.
                self.set_interaction_mode(self.InteractionMode.NOOP)
                self.cut_intersecting_links()
                self.cutline.clear()
                event.accept()
                return

            if self.interaction_mode is self.InteractionMode.RUBBER_BAND:
                # Qt ends the band and hides its rectangle. The selection is still held
                # back while it does, and synced once the band is over.
                try:
                    super().mouseReleaseEvent(event)
                finally:
                    self.set_interaction_mode(self.InteractionMode.NOOP)
                self.gr_stage.on_selection_changed()
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

    # Middle mouse
    def middle_mouse_press(self, event: QtGui.QMouseEvent):
        """Start panning the view with the middle button.

        Args:
            event (QtGui.QMouseEvent): event.
        """
        release_event = QtGui.QMouseEvent(
            QtCore.QEvent.MouseButtonRelease,
            event.position(),
            event.globalPosition(),
            QtCore.Qt.LeftButton,
            QtCore.Qt.NoButton,
            event.modifiers(),
        )
        super().mouseReleaseEvent(release_event)
        self.setInteractive(False)
        self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
        fake_event = QtGui.QMouseEvent(
            event.type(),
            event.position(),
            event.globalPosition(),
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
            event.position(),
            event.globalPosition(),
            QtGui.Qt.LeftButton,
            event.buttons() & ~QtGui.Qt.LeftButton,
            event.modifiers(),
        )
        super().mouseReleaseEvent(fake_event)
        self.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
        self.setInteractive(True)

    # Dragging
    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:
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
        state = self.get_current_state()
        if not state.is_idle:
            return
        ACTION_ROUTER.refresh_enabled()
        menu = context_menus.build_nodes_context_menu(
            self,
            has_selection=state.has_selection,
            has_reference=any(
                gr_node.node.get_source_file() is not None
                for gr_node in self.gr_stage.selected_gr_nodes()
            ),
        )
        context_menus.show_menu(menu, self.mapToGlobal(point))

    def cut_intersecting_links(self) -> bool:
        """Unlink the links crossed by the cutline.

        Returns:
            bool: at least one link was cut.
        """
        return self.gr_stage.cut_links_along(self.cutline.line_points)

    def create_new_node(self):
        """Show the nodes palette at the last mouse position."""
        self.graph_editor.show_nodes_palette_centered(self.last_scene_mouse_pos)

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

        self.zoom = self.zoom_controller.zoom_to_fit(viewport_rect.size(), padded_rect)
        self.setTransform(self.zoom_controller.transform)
        self.centerOn(padded_rect.center())
        self.update_render_hints()
