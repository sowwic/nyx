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

        self.line_points = []
        self._pen = QtGui.QPen(QtCore.Qt.white)
        self._pen.setWidthF(2.0)
        self._pen.setDashPattern([3, 3])

        self.setZValue(2)

    def boundingRect(self):
        """QtCore.QRectF: bounds of the line."""
        return self.shape().boundingRect()

    def shape(self):
        """QtGui.QPainterPath: path through the line points."""
        if len(self.line_points) > 1:
            path = QtGui.QPainterPath(self.line_points[0])
            for pt in self.line_points[1:]:
                path.lineTo(pt)
        else:
            path = QtGui.QPainterPath(QtCore.QPointF(0.0, 0.0))
            path.lineTo(QtCore.QPointF(1.0, 1.0))
        return path

    def paint(self, painter, option, widget=None):
        """Draw the line as a polyline.

        Args:
            painter (QtGui.QPainter): painter.
            option (QtWidgets.QStyleOptionGraphicsItem): style options.
            widget (QtWidgets.QWidget | None): painted widget.
        """
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setPen(self._pen)

        poly = QtGui.QPolygonF(self.line_points)
        painter.drawPolyline(poly)
