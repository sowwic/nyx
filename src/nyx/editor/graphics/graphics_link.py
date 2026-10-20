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
    """

    WIDTH = 2.0
    PREVIEW_OPACITY = 0.8
    MIN_TANGENT = 40.0

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
        # The gradient runs between the anchors, so it follows them.
        self.update_style()
