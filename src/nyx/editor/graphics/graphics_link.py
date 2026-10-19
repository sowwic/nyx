import typing
from uuid import UUID

from PySide6 import QtCore, QtGui, QtWidgets

if typing.TYPE_CHECKING:
    from nyx.editor.graphics.graphics_plug import GraphicsPlug


class GraphicsLink(QtWidgets.QGraphicsPathItem):
    """Curve between the output socket of one plug and the input socket of another.

    A link with a missing end is a preview that is being dragged: the missing
    end follows `floating_pos`. Previews are never attached to plugs, only
    complete links are (see `attach`).
    """

    COLOR = QtGui.QColor("#FFA637")
    PREVIEW_COLOR = QtGui.QColor("#99FFA637")
    WIDTH = 2.0
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

        is_preview = source_plug is None or target_plug is None
        pen = QtGui.QPen(self.PREVIEW_COLOR if is_preview else self.COLOR, self.WIDTH)
        pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        self.setPen(pen)
        # Links are drawn behind nodes, previews above everything.
        self.setZValue(1 if is_preview else -1)
        if is_preview:
            self.setAcceptedMouseButtons(QtCore.Qt.MouseButton.NoButton)
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
