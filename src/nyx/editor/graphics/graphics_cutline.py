from PySide6 import QtCore, QtGui, QtWidgets


class GraphCutLine(QtWidgets.QGraphicsItem):
    """Dashed line drawn while cutting links with the mouse.

    Attributes:
        line_points: scene points the line passes through
    """

    def __init__(self, parent=None):
        """Initialize GraphCutLine.

        Args:
            parent (QtWidgets.QGraphicsItem | None): parent item.
        """
        super().__init__(parent)

        self._line_points: list[QtCore.QPointF] = []
        self._pen = QtGui.QPen(QtCore.Qt.white)
        self._pen.setWidthF(2.0)
        self._pen.setDashPattern([3, 3])

        self.setZValue(2)

    @property
    def line_points(self) -> list[QtCore.QPointF]:
        """list[QtCore.QPointF]: scene points the line passes through."""
        return self._line_points

    @line_points.setter
    def line_points(self, points: list[QtCore.QPointF]):
        """Replace the points and schedule a repaint.

        Args:
            points (list[QtCore.QPointF]): new points.
        """
        self.prepareGeometryChange()
        self._line_points = list(points)
        self.update()

    def add_point(self, point: QtCore.QPointF):
        """Extend the line.

        Args:
            point (QtCore.QPointF): scene point to add.
        """
        self.prepareGeometryChange()
        self._line_points.append(point)
        self.update()

    def clear(self):
        """Remove all points."""
        self.line_points = []

    def boundingRect(self) -> QtCore.QRectF:
        """QtCore.QRectF: bounds of the line, including the pen width."""
        if not self._line_points:
            return QtCore.QRectF()
        margin = self._pen.widthF()
        return (
            QtGui.QPolygonF(self._line_points)
            .boundingRect()
            .adjusted(-margin, -margin, margin, margin)
        )

    def shape(self) -> QtGui.QPainterPath:
        """QtGui.QPainterPath: path through the line points."""
        path = QtGui.QPainterPath()
        if len(self._line_points) > 1:
            path.moveTo(self._line_points[0])
            for pt in self._line_points[1:]:
                path.lineTo(pt)
        return path

    def paint(self, painter, option, widget=None):
        """Draw the line as a polyline.

        Args:
            painter (QtGui.QPainter): painter.
            option (QtWidgets.QStyleOptionGraphicsItem): style options.
            widget (QtWidgets.QWidget | None): painted widget.
        """
        if len(self._line_points) < 2:
            return
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setPen(self._pen)
        painter.drawPolyline(QtGui.QPolygonF(self._line_points))
