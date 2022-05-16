import typing
import enum
# import pathlib
from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets

from nyx import get_main_logger
from nyx.editor.graphics.graphics_cutline import GraphCutLine

if typing.TYPE_CHECKING:
    from nyx.editor.widgets.stage_graph_editor import StageGraphEditor


LOGGER = get_main_logger()


class StageGraphView(QtWidgets.QGraphicsView):

    # Signals
    item_drag_entered = QtCore.Signal(QtGui.QDragEnterEvent)
    item_dropped = QtCore.Signal(QtGui.QDropEvent)

    # Constants
    EDGE_DRAG_START_THRESHOLD = 50
    HIGH_QUALITY_ZOOM = 4

    class InteractionMode(enum.Enum):
        NOOP = enum.auto()
        EDGE_DRAG = enum.auto()
        EDGE_CUT = enum.auto()

    def __init__(self, graph_editor: "StageGraphEditor", parent: QtWidgets.QWidget = None) -> None:

        super().__init__(graph_editor.gr_scene, parent=parent)
        self.graph_editor: "StageGraphEditor" = graph_editor
        self.cutline = GraphCutLine()
        self.scene().addItem(self.cutline)
        self.__interaction_mode = StageGraphView.InteractionMode.NOOP

        # Zoom
        self.zoom_in_factor = 1.25
        self.zoom_clamp = True
        self.zoom = 10
        self.zoom_step = 1
        self.zoom_range = (-5.0, 10.0)
        # Positions
        self.last_lmb_click_pos = QtCore.QPointF(0.0, 0.0)
        self.last_scene_mouse_pos = QtCore.QPointF(0.0, 0.0)
        # Toggles
        self.rubberband_dragging_rect = False

        self.__setup_view()
        self.update_render_hints()
        self.create_actions()
        self.create_widgets()
        self.create_layouts()
        self.create_connections()

    def __setup_view(self):
        self.setInteractive(True)
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
        self.setAcceptDrops(True)

    def update_render_hints(self):
        if self.zoom > self.HIGH_QUALITY_ZOOM:
            self.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.HighQualityAntialiasing |
                                QtGui.QPainter.TextAntialiasing | QtGui.QPainter.SmoothPixmapTransform)
        else:
            self.setRenderHints(QtGui.QPainter.Antialiasing |
                                QtGui.QPainter.TextAntialiasing | QtGui.QPainter.SmoothPixmapTransform)

    def create_actions(self):
        pass

    def create_widgets(self):
        pass

    def create_layouts(self):
        pass

    def create_connections(self):
        pass

    @property
    def stage(self):
        return self.graph_editor.stage

    @property
    def is_dragging(self):
        return not self.isInteractive()

    @property
    def interaction_mode(self):
        return self.__interaction_mode

    def set_interaction_mode(self, mode: "StageGraphView.InteractionMode"):
        self.__interaction_mode = mode
        LOGGER.debug(f"Interaction mode: {mode}")

    def get_center_position(self) -> QtCore.QPointF:
        return self.mapToScene(self.viewport().rect().center())

    # Mouse
    def wheelEvent(self, event: QtGui.QWheelEvent):
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

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.MiddleButton:
            self.middle_mouse_press(event)
        elif event.button() == QtCore.Qt.LeftButton:
            self.left_mouse_press(event)
        elif event.button() == QtCore.Qt.RightButton:
            self.right_mouse_press(event)
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.MiddleButton:
            self.middle_mouse_release(event)
        elif event.button() == QtCore.Qt.LeftButton:
            self.left_mouse_release(event)
        elif event.button() == QtCore.Qt.RightButton:
            self.right_mouse_release(event)
        else:
            super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
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
            LOGGER.exception('mouseMoveEvent exception')

        self.last_scene_mouse_pos = scene_pos
        super().mouseMoveEvent(event)

    def left_mouse_press(self, event: QtGui.QMouseEvent):
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
                fake_event = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonRelease, event.localPos(), event.screenPos(),
                                               QtCore.Qt.LeftButton, QtCore.Qt.NoButton, event.modifiers())
                super().mouseReleaseEvent(fake_event)
                event.ignore()
                return
            else:
                self.rubberband_dragging_rect = True

        super().mousePressEvent(event)

    def left_mouse_release(self, event: QtGui.QMouseEvent):
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
                # self.scene.on_selection_change()
                event.accept()
                return
        except Exception:
            LOGGER.exception('Left mouse release exception')

        super().mouseReleaseEvent(event)

    # Right mouse
    def right_mouse_press(self, mouse_event: QtGui.QMouseEvent):
        release_event = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonRelease, mouse_event.localPos(), mouse_event.screenPos(),
                                          QtCore.Qt.LeftButton, QtCore.Qt.NoButton, mouse_event.modifiers())
        super().mouseReleaseEvent(release_event)
        self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
        self.setInteractive(False)
        fake_event = QtGui.QMouseEvent(mouse_event.type(), mouse_event.localPos(), mouse_event.screenPos(),
                                       QtCore.Qt.LeftButton, mouse_event.buttons() | QtCore.Qt.LeftButton, mouse_event.modifiers())
        super().mousePressEvent(fake_event)
        mouse_event.ignore()

    def right_mouse_release(self, event: QtGui.QMouseEvent):
        fake_event = QtGui.QMouseEvent(event.type(), event.localPos(), event.screenPos(),
                                       QtCore.Qt.LeftButton, event.buttons() & ~QtCore.Qt.LeftButton, event.modifiers())
        super().mouseReleaseEvent(fake_event)
        self.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
        self.setInteractive(True)
        event.ignore()

    def get_item_at_click(self, event: QtGui.QMouseEvent) -> "QtWidgets.QGraphicsItem | None":
        """Object at click event position"""
        item = self.itemAt(event.pos())
        return item

    # Middle mouse
    def middle_mouse_press(self, event: QtGui.QMouseEvent):
        event.ignore()
        return

    def middle_mouse_release(self, event: QtGui.QMouseEvent):
        event.ignore()
        return

    # Dragging
    def dragEnterEvent(self, event: QtGui.QDragEnterEvent):
        self.item_drag_entered.emit(event)

    def dropEvent(self, event: QtGui.QDropEvent):
        self.item_dropped.emit(event)

    def cut_intersecting_edges(self):
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
            # TODO: Disconnect attributes here
            pass
            # self.scene.history.store_history('Edges cut', set_modified=True)

    def rebuild_current_scope(self):
        self.scene().clear()
