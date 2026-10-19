import abc
import math

from PySide6 import QtCore, QtGui

from nyx.static.enums import GraphicsPlugShape


class PlugShape(abc.ABC):
    """Look of the socket of a plug.

    A shape holds no state: the plug tells it where to draw, with which color and
    whether the socket is linked. Subclasses implement `paint`.

    Attributes:
        RADIUS: half the size of the drawn socket, the label keeps clear of it
        HIT_RADIUS: distance from the center of the socket that still grabs it
    """

    RADIUS = 5.0
    HIT_RADIUS = 9.0
    OUTLINE_COLOR = QtGui.QColor("#7F000000")

    @abc.abstractmethod
    def paint(
        self,
        painter: QtGui.QPainter,
        center: QtCore.QPointF,
        color: QtGui.QColor,
        linked: bool,
    ) -> None:
        """Draw a socket.

        Args:
            painter (QtGui.QPainter): painter, in the coordinates of the plug.
            center (QtCore.QPointF): center of the socket.
            color (QtGui.QColor): color of the plug.
            linked (bool): a link is attached to the socket.
        """

    def contains(self, offset: QtCore.QPointF) -> bool:
        """Check whether a point grabs the socket.

        Args:
            offset (QtCore.QPointF): point relative to the center of the socket.

        Returns:
            bool: point is within reach of the socket.
        """
        return math.hypot(offset.x(), offset.y()) <= self.HIT_RADIUS


class CirclePlugShape(PlugShape):
    """Filled circle, with a dark hole while the socket is not linked."""

    HOLE_COLOR = QtGui.QColor("black")
    HOLE_RADIUS = 3.5

    def paint(
        self,
        painter: QtGui.QPainter,
        center: QtCore.QPointF,
        color: QtGui.QColor,
        linked: bool,
    ) -> None:
        """Draw the circle.

        Args:
            painter (QtGui.QPainter): painter, in the coordinates of the plug.
            center (QtCore.QPointF): center of the socket.
            color (QtGui.QColor): color of the circle.
            linked (bool): no hole when a link is attached.
        """
        painter.setPen(QtGui.QPen(self.OUTLINE_COLOR, 1.0))
        painter.setBrush(color)
        painter.drawEllipse(center, self.RADIUS, self.RADIUS)
        if not linked:
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(self.HOLE_COLOR)
            painter.drawEllipse(center, self.HOLE_RADIUS, self.HOLE_RADIUS)


class TrianglePlugShape(PlugShape):
    """Triangle pointing along the flow, outlined until the socket is linked."""

    OUTLINE_WIDTH = 1.5

    def polygon(self, center: QtCore.QPointF) -> QtGui.QPolygonF:
        """Get the corners of the triangle.

        Args:
            center (QtCore.QPointF): center of the socket.

        Returns:
            QtGui.QPolygonF: left top, left bottom and the tip pointing right.
        """
        r = self.RADIUS
        return QtGui.QPolygonF(
            [
                QtCore.QPointF(center.x() - 0.8 * r, center.y() - r),
                QtCore.QPointF(center.x() - 0.8 * r, center.y() + r),
                QtCore.QPointF(center.x() + r, center.y()),
            ]
        )

    def paint(
        self,
        painter: QtGui.QPainter,
        center: QtCore.QPointF,
        color: QtGui.QColor,
        linked: bool,
    ) -> None:
        """Draw the triangle.

        Args:
            painter (QtGui.QPainter): painter, in the coordinates of the plug.
            center (QtCore.QPointF): center of the socket.
            color (QtGui.QColor): color of the outline, and of the fill when linked.
            linked (bool): filled when a link is attached, otherwise only outlined.
        """
        pen = QtGui.QPen(color, self.OUTLINE_WIDTH)
        pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(color if linked else QtCore.Qt.BrushStyle.NoBrush)
        painter.drawPolygon(self.polygon(center))


PLUG_SHAPES: dict[GraphicsPlugShape, PlugShape] = {
    GraphicsPlugShape.CIRCLE: CirclePlugShape(),
    GraphicsPlugShape.TRIANGLE: TrianglePlugShape(),
}


def plug_shape_for(shape: GraphicsPlugShape) -> PlugShape:
    """Get the object drawing a kind of shape.

    Args:
        shape (GraphicsPlugShape): kind of shape a component asks for.

    Returns:
        PlugShape: drawing for the shape, the circle for a shape without one.
    """
    return PLUG_SHAPES.get(shape, PLUG_SHAPES[GraphicsPlugShape.CIRCLE])
