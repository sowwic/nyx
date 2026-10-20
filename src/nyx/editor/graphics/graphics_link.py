import typing
from uuid import UUID

from PySide6 import QtCore, QtGui, QtWidgets

from nyx.core.node_component import NodeComponent

if typing.TYPE_CHECKING:
    from nyx.editor.graphics.graphics_plug import GraphicsPlug


class GraphicsLink(QtWidgets.QGraphicsPathItem):
    """Curve between the output socket of one plug and the input socket of another.

    A link with a missing end is a preview that is being dragged: the missing
    end follows `floating_pos`. Previews are never attached to plugs, only
    complete links are (see `attach`).

    The link is drawn like the component it comes from: its color, and a width that
    the component scales. A link between plugs of different colors fades from the
    color of the source to the one of the target.

    A link on the execution chain can pulse: a dot with a short tail travels from the
    source to the target. The link only draws what it is told to, `LinkPulseAnimator`
    decides when and how far the pulse is.
    """

    WIDTH = 2.0
    PREVIEW_OPACITY = 0.8
    MIN_TANGENT = 40.0

    PULSE_COLOR = QtGui.QColor("#4BE3FF")
    PULSE_SPEED = 160.0  # scene units per second
    PULSE_RADIUS = 3.5
    PULSE_TAIL_SAMPLES = 6
    PULSE_TAIL_STEP = 6.0

    def __init__(
        self,
        source_plug: GraphicsPlug | None = None,
        target_plug: GraphicsPlug | None = None,
        link_uuid: UUID | None = None,
    ):
        """Initialize GraphicsLink.

        Args:
            source_plug (GraphicsPlug | None): plug the link starts at.
            target_plug (GraphicsPlug | None): plug the link ends at.
            link_uuid (UUID | None): uuid of the link in the stage, None for previews.
        """
        super().__init__()
        self._source_plug = source_plug
        self._target_plug = target_plug
        self._uuid = link_uuid
        self._floating_pos = QtCore.QPointF()
        self._attached = False
        self._pulsing = False
        self._pulse_offset: float | None = None
        self._path_length = 0.0

        # Links are drawn behind nodes, previews above everything.
        self.setZValue(1 if self.is_preview else -1)
        if self.is_preview:
            self.setAcceptedMouseButtons(QtCore.Qt.MouseButton.NoButton)
        self.update_style()
        self.update_path()

    @property
    def uuid(self) -> UUID | None:
        """UUID | None: uuid of the link in the stage, None for previews."""
        return self._uuid

    @property
    def source_plug(self) -> GraphicsPlug | None:
        """GraphicsPlug | None: plug the link starts at."""
        return self._source_plug

    @property
    def target_plug(self) -> GraphicsPlug | None:
        """GraphicsPlug | None: plug the link ends at."""
        return self._target_plug

    @property
    def is_preview(self) -> bool:
        """bool: link is missing an end."""
        return self._source_plug is None or self._target_plug is None

    @property
    def style_plug(self) -> GraphicsPlug | None:
        """GraphicsPlug | None: plug the look of the link comes from.

        The source of the link, or for a preview dragged from an input socket the plug
        it is dragged from.
        """
        return self._source_plug if self._source_plug is not None else self._target_plug

    @property
    def is_pulsing(self) -> bool:
        """bool: the link is part of the execution chain and can show a pulse."""
        return self._pulsing

    @property
    def pulse_offset(self) -> float | None:
        """float | None: distance of the pulse along the link, None if not shown."""
        return self._pulse_offset

    def set_pulsing(self, state: bool):
        """Mark the link as pulsing or not.

        Args:
            state (bool): the link is part of the execution chain.
        """
        if state == self._pulsing:
            return
        # The pulse is bigger than the stroke, so the bounds change with it.
        self.prepareGeometryChange()
        self._pulsing = state
        if not state:
            self._pulse_offset = None
        self.update()

    def set_pulse_offset(self, offset: float | None):
        """Move the pulse.

        Args:
            offset (float | None): distance from the source along the curve, wrapped
                around the length of the link. None hides the pulse.
        """
        if not self._pulsing:
            return
        self._pulse_offset = offset
        self.update()

    def boundingRect(self) -> QtCore.QRectF:
        """QtCore.QRectF: bounds of the stroke, with room for the pulse."""
        rect = super().boundingRect()
        if not self._pulsing:
            return rect
        margin = self.PULSE_RADIUS
        return rect.adjusted(-margin, -margin, margin, margin)

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionGraphicsItem,
        widget: QtWidgets.QWidget | None = None,
    ) -> None:
        """Paint the link, then the pulse on top of it.

        Args:
            painter (QtGui.QPainter): painter.
            option (QtWidgets.QStyleOptionGraphicsItem): style option.
            widget (QtWidgets.QWidget | None): widget being painted on.
        """
        super().paint(painter, option, widget)
        self._paint_pulse(painter)

    def _paint_pulse(self, painter: QtGui.QPainter):
        """Draw the pulse: a dot at the offset followed by a fading tail.

        Args:
            painter (QtGui.QPainter): painter.
        """
        if self._pulse_offset is None or self.is_preview or self._path_length <= 0:
            return

        path = self.path()
        head = self._pulse_offset % self._path_length
        color = QtGui.QColor(self.PULSE_COLOR)
        painter.save()
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        for sample in range(self.PULSE_TAIL_SAMPLES):
            distance = head - sample * self.PULSE_TAIL_STEP
            if distance < 0:
                break
            fade = sample / self.PULSE_TAIL_SAMPLES
            color.setAlphaF(1.0 - fade)
            painter.setBrush(color)
            radius = self.PULSE_RADIUS * (1.0 - 0.5 * fade)
            point = path.pointAtPercent(path.percentAtLength(distance))
            painter.drawEllipse(point, radius, radius)
        painter.restore()

    def update_style(self):
        """Take color and width from the plug the link comes from.

        A complete link whose plugs differ in color is stroked with a gradient.
        """
        plug = self.style_plug
        color = (
            plug.color
            if plug is not None
            else QtGui.QColor(NodeComponent.DEFAULT_PLUG_COLOR)
        )
        width = self.WIDTH * (plug.link_width_multiplier if plug is not None else 1.0)
        if self.is_preview:
            color.setAlphaF(color.alphaF() * self.PREVIEW_OPACITY)
        pen = QtGui.QPen(self._build_stroke_brush(color), width)
        pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        self.setPen(pen)

    def _build_stroke_brush(self, color: QtGui.QColor) -> QtGui.QBrush:
        """Build the brush the link is stroked with.

        Args:
            color (QtGui.QColor): color of the plug the link comes from.

        Returns:
            QtGui.QBrush: solid brush, or a gradient from the source to the target
                color for a complete link between plugs of different colors.
        """
        if self.is_preview or self._target_plug.color == color:
            return QtGui.QBrush(color)

        gradient = QtGui.QLinearGradient(
            self._source_plug.output_anchor(), self._target_plug.input_anchor()
        )
        gradient.setColorAt(0.0, color)
        gradient.setColorAt(1.0, self._target_plug.color)
        return QtGui.QBrush(gradient)

    def set_floating_pos(self, scene_pos: QtCore.QPointF):
        """Move the open end of a preview.

        Args:
            scene_pos (QtCore.QPointF): scene position of the open end.
        """
        self._floating_pos = QtCore.QPointF(scene_pos)
        self.update_path()

    def attach(self):
        """Register the link on both of its plugs so it follows them."""
        if self._attached or self.is_preview:
            return
        self._source_plug.add_link(self)
        self._target_plug.add_link(self)
        self._attached = True

    def detach(self):
        """Unregister the link from its plugs."""
        if not self._attached:
            return
        self._source_plug.discard_link(self)
        self._target_plug.discard_link(self)
        self._attached = False

    def update_path(self):
        """Rebuild the curve from the current anchors."""
        start = (
            self._source_plug.output_anchor()
            if self._source_plug
            else self._floating_pos
        )
        end = (
            self._target_plug.input_anchor() if self._target_plug else self._floating_pos
        )
        tangent = max(self.MIN_TANGENT, abs(end.x() - start.x()) * 0.5)
        path = QtGui.QPainterPath(start)
        path.cubicTo(
            start + QtCore.QPointF(tangent, 0.0),
            end - QtCore.QPointF(tangent, 0.0),
            end,
        )
        self.setPath(path)
        self._path_length = path.length()
        # The gradient runs between the anchors, so it follows them.
        self.update_style()
