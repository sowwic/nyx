import enum
import typing
from uuid import UUID

from PySide6 import QtCore, QtGui, QtWidgets

from nyx.editor.graphics.graphics_plug_shape import PlugShape, plug_shape_for
from nyx.editor.graphics.level_of_detail import LevelOfDetail
from nyx.editor.utils.common import (
    are_hover_diagnostics_enabled,
    build_role_tooltip_html,
)
from nyx.static.enums import GraphicsPlugShape

if typing.TYPE_CHECKING:
    from nyx.core.node_component import NodeComponent
    from nyx.editor.graphics.graphics_link import GraphicsLink
    from nyx.editor.graphics.graphics_node import GraphicsNode


class GraphicsPlug(QtWidgets.QGraphicsItem):
    """Row of a graphics node representing a component that can be linked.

    The plug is a child of its `GraphicsNode`. It owns its geometry and exposes
    anchors in scene coordinates so links can attach to it.
    """

    class Socket(enum.Enum):
        """Side of the plug a socket is on."""

        INPUT = enum.auto()
        OUTPUT = enum.auto()

    ROW_HEIGHT = 20.0
    SOCKET_INSET = 10.0  # distance of the sockets from the sides of the node
    LABEL_COLOR = QtGui.QColor("#CCCCCC")
    LABEL_FONT = QtGui.QFont("Zed Mono", 10)

    def __init__(self, component: NodeComponent, gr_node: GraphicsNode):
        """Initialize GraphicsPlug.

        Args:
            component (NodeComponent): component represented by the plug.
            gr_node (GraphicsNode): graphics node owning the plug.
        """
        super().__init__(gr_node)
        self._component = component
        self._uuid: UUID = component.uuid
        self._width = gr_node.width
        self._label = component.name
        self._writable = False
        self._readable = False
        self._input_linked = False
        self._output_linked = False
        self._shape_kind: GraphicsPlugShape | None = None
        self._shape: PlugShape = plug_shape_for(GraphicsPlugShape.CIRCLE)
        self._color = QtGui.QColor()
        self._link_width_multiplier = 1.0
        self._links: set[GraphicsLink] = set()
        self._level_of_detail = LevelOfDetail.FULL  # as of the last paint
        self.setAcceptHoverEvents(True)
        self.refresh()

    @property
    def component(self) -> NodeComponent:
        """NodeComponent: component represented by the plug."""
        return self._component

    @property
    def uuid(self) -> UUID:
        """UUID: uuid of the component. Stable key for the plug."""
        return self._uuid

    @property
    def gr_node(self) -> GraphicsNode:
        """GraphicsNode: node owning the plug."""
        return self.parentItem()

    @property
    def shape(self) -> PlugShape:
        """PlugShape: drawing of the sockets, chosen by the component."""
        return self._shape

    @property
    def color(self) -> QtGui.QColor:
        """QtGui.QColor: color of the sockets, chosen by the component."""
        return QtGui.QColor(self._color)

    @property
    def link_width_multiplier(self) -> float:
        """float: how thick links of the plug are drawn, chosen by the component."""
        return self._link_width_multiplier

    @property
    def links(self) -> list[GraphicsLink]:
        """list[GraphicsLink]: links attached to the plug."""
        return list(self._links)

    @staticmethod
    def is_plug_component(component: NodeComponent) -> bool:
        """Check if the component should be shown as a plug.

        Args:
            component (NodeComponent): component to check.

        Returns:
            bool: component accepts input or produces output.
        """
        return component.writable or component.readable

    def refresh(self):
        """Re-read the state of the component and repaint if it changed."""
        state = (
            self._component.name,
            self._component.writable,
            self._component.readable,
            bool(self._component.input_links_uuids),
            bool(self._component.output_links_uuids),
            self._component.get_plug_shape(),
            self._component.get_plug_color(),
            type(self._component).get_link_width_multiplier(),
        )
        if state == (
            self._label,
            self._writable,
            self._readable,
            self._input_linked,
            self._output_linked,
            self._shape_kind,
            self._color,
            self._link_width_multiplier,
        ):
            return
        (
            self._label,
            self._writable,
            self._readable,
            self._input_linked,
            self._output_linked,
            self._shape_kind,
            self._color,
            self._link_width_multiplier,
        ) = state
        self._shape = plug_shape_for(self._shape_kind)
        for link in self._links:
            link.update_style()
        self.update()

    def set_width(self, width: float):
        """Set the width of the row.

        Args:
            width (float): new width, usually the width of the node.
        """
        if width == self._width:
            return
        self.prepareGeometryChange()
        self._width = width

    @property
    def _input_x(self) -> float:
        """float: x of the input socket, in the coordinates of the plug."""
        return self.SOCKET_INSET

    @property
    def _output_x(self) -> float:
        """float: x of the output socket, in the coordinates of the plug."""
        return self._width - self.SOCKET_INSET

    def input_anchor(self) -> QtCore.QPointF:
        """QtCore.QPointF: scene position input links should attach to."""
        return self.mapToScene(self._input_x, self.ROW_HEIGHT / 2)

    def output_anchor(self) -> QtCore.QPointF:
        """QtCore.QPointF: scene position output links should attach to."""
        return self.mapToScene(self._output_x, self.ROW_HEIGHT / 2)

    def _label_margins(self) -> tuple[float, float]:
        """Get the space the label keeps clear of the sides of the row.

        Returns:
            tuple[float, float]: left and right margin. Room for the socket on a side
                that has one, a small padding on the other.
        """
        socket_room = self.SOCKET_INSET + self._shape.RADIUS * 2 + 2
        return (
            socket_room if self._writable else self.SOCKET_INSET,
            socket_room if self._readable else self.SOCKET_INSET,
        )

    def preferred_width(self) -> float:
        """Get the width the row needs to show its label next to its sockets.

        Returns:
            float: width of the label plus its margins.
        """
        left, right = self._label_margins()
        text_width = QtGui.QFontMetricsF(self.LABEL_FONT).horizontalAdvance(self._label)
        return left + text_width + right

    def add_link(self, link: GraphicsLink):
        """Track a link so it can follow the plug.

        Args:
            link (GraphicsLink): link attached to the plug.
        """
        self._links.add(link)

    def discard_link(self, link: GraphicsLink):
        """Stop tracking a link.

        Args:
            link (GraphicsLink): link to forget.
        """
        self._links.discard(link)

    def update_links(self):
        """Redraw the attached links after the plug (or its node) moved."""
        for link in self._links:
            link.update_path()

    def socket_at(self, scene_pos: QtCore.QPointF) -> Socket | None:
        """Find the visible socket under a scene position.

        Args:
            scene_pos (QtCore.QPointF): scene position.

        Returns:
            GraphicsPlug.Socket | None: socket hit, None if there is none.
        """
        if not self._level_of_detail.shows_shapes:
            return None
        local = self.mapFromScene(scene_pos)
        center_y = self.ROW_HEIGHT / 2
        if self._writable and self._shape.contains(
            QtCore.QPointF(local.x() - self._input_x, local.y() - center_y)
        ):
            return self.Socket.INPUT
        if self._readable and self._shape.contains(
            QtCore.QPointF(local.x() - self._output_x, local.y() - center_y)
        ):
            return self.Socket.OUTPUT
        return None

    def boundingRect(self) -> QtCore.QRectF:
        """QtCore.QRectF: bounds of the row, the sockets are inside of it."""
        return QtCore.QRectF(0.0, 0.0, self._width, self.ROW_HEIGHT)

    # ======== Events ========= #

    def _refresh_tooltip(self):
        """Show the roles of the component as tooltip if diagnostics are enabled."""
        index = self._component.index()
        if not index.isValid():
            return

        if are_hover_diagnostics_enabled():
            self.setToolTip(build_role_tooltip_html(index))

    def hoverEnterEvent(self, event: QtWidgets.QGraphicsSceneHoverEvent) -> None:
        """Refresh the tooltip when the cursor enters.

        Args:
            event (QtWidgets.QGraphicsSceneHoverEvent): event.
        """
        self._refresh_tooltip()
        super().hoverEnterEvent(event)

    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        """Start dragging a link from the socket under the cursor.

        Presses outside of the sockets are passed on to the node.

        Args:
            event (QtWidgets.QGraphicsSceneMouseEvent): event.
        """
        gr_stage = self.scene()
        socket = self.socket_at(event.scenePos())
        if (
            event.button() == QtCore.Qt.MouseButton.LeftButton
            and socket is not None
            and gr_stage is not None
        ):
            gr_stage.begin_link_drag(self, socket)
            event.accept()
            return
        event.ignore()

    def mouseMoveEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        """Move the open end of the dragged link.

        Args:
            event (QtWidgets.QGraphicsSceneMouseEvent): event.
        """
        gr_stage = self.scene()
        if gr_stage is not None and gr_stage.is_dragging_link:
            gr_stage.update_link_drag(event.scenePos())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        """Drop the dragged link.

        Args:
            event (QtWidgets.QGraphicsSceneMouseEvent): event.
        """
        gr_stage = self.scene()
        if gr_stage is not None and gr_stage.is_dragging_link:
            gr_stage.finish_link_drag(event.scenePos())
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionGraphicsItem,
        widget: QtWidgets.QWidget | None = None,
    ) -> None:
        """Draw sockets and the component name, as far as they are big enough to see.

        Args:
            painter (QtGui.QPainter): painter.
            option (QtWidgets.QStyleOptionGraphicsItem): style options.
            widget (QtWidgets.QWidget | None): painted widget.
        """
        self._level_of_detail = LevelOfDetail.from_painter(
            painter,
            text_size=self.LABEL_FONT.pointSizeF(),
            shape_size=self.ROW_HEIGHT,
        )
        if not self._level_of_detail.shows_shapes:
            return

        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        center_y = self.ROW_HEIGHT / 2
        # (center, is linked) per visible socket
        sockets = []
        if self._writable:
            sockets.append((QtCore.QPointF(self._input_x, center_y), self._input_linked))
        if self._readable:
            sockets.append(
                (QtCore.QPointF(self._output_x, center_y), self._output_linked)
            )

        for center, linked in sockets:
            self._shape.paint(painter, center, self._color, linked)

        if not self._level_of_detail.shows_text:
            return

        painter.setFont(self.LABEL_FONT)
        painter.setPen(self.LABEL_COLOR)
        left, right = self._label_margins()
        text_rect = QtCore.QRectF(left, 0.0, self._width - left - right, self.ROW_HEIGHT)
        align = (
            QtCore.Qt.AlignmentFlag.AlignRight
            if self._readable and not self._writable
            else QtCore.Qt.AlignmentFlag.AlignLeft
        ) | QtCore.Qt.AlignmentFlag.AlignVCenter
        painter.drawText(text_rect, align, self._label)
