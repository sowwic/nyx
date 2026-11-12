import typing

from PySide6 import QtCore, QtGui, QtWidgets

if typing.TYPE_CHECKING:
    from nyx.editor.graphics.graphics_link import GraphicsLink


class GraphicsLinkPin(QtWidgets.QGraphicsEllipseItem):
    """Dot on a link that the link is drawn through.

    The pin is moved with the mouse and removed with a double click. The link follows
    it while it moves, the move is pushed to the stage when the mouse is released.
    """

    RADIUS = 5.0
    HOVER_SCALE = 1.4

    def __init__(self, link: GraphicsLink, pos: QtCore.QPointF):
        """Initialize GraphicsLinkPin.

        Args:
            link (GraphicsLink): link the pin is on.
            pos (QtCore.QPointF): position of the pin in the scene.
        """
        super().__init__(
            -self.RADIUS, -self.RADIUS, self.RADIUS * 2, self.RADIUS * 2, parent=link
        )
        self._link = link
        self._press_pos: QtCore.QPointF | None = None
        self.setPos(pos)
        self.setFlags(
            QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemSendsScenePositionChanges
        )
        self.setAcceptHoverEvents(True)
        self.setCursor(QtCore.Qt.CursorShape.SizeAllCursor)
        self.update_style()

    @property
    def link(self) -> GraphicsLink:
        """GraphicsLink: link the pin is on."""
        return self._link

    def update_style(self):
        """Take the color from the link."""
        color = self._link.pin_color
        self.setBrush(QtGui.QBrush(color))
        outline = QtGui.QPen(color.darker(160), 1.0)
        outline.setCosmetic(True)
        self.setPen(outline)

    def itemChange(self, change, value):
        """Redraw the link when the pin moves.

        Args:
            change (QtWidgets.QGraphicsItem.GraphicsItemChange): kind of change.
            value (typing.Any): new value.

        Returns:
            typing.Any: value to apply.
        """
        if (
            change
            == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemScenePositionHasChanged
        ):
            self._link.on_pin_moved()
        return super().itemChange(change, value)

    def hoverEnterEvent(self, event: QtWidgets.QGraphicsSceneHoverEvent) -> None:
        """Enlarge the pin.

        Args:
            event (QtWidgets.QGraphicsSceneHoverEvent): event.
        """
        self.setScale(self.HOVER_SCALE)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: QtWidgets.QGraphicsSceneHoverEvent) -> None:
        """Restore the size of the pin.

        Args:
            event (QtWidgets.QGraphicsSceneHoverEvent): event.
        """
        self.setScale(1.0)
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        """Remember where the pin was to tell later whether it moved.

        Args:
            event (QtWidgets.QGraphicsSceneMouseEvent): event.
        """
        self._press_pos = self.scenePos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        """Push the move to the stage.

        Args:
            event (QtWidgets.QGraphicsSceneMouseEvent): event.
        """
        super().mouseReleaseEvent(event)
        moved = self._press_pos is not None and self.scenePos() != self._press_pos
        self._press_pos = None
        # The scene is rebuilt by the command, which deletes this item.
        if moved:
            self._link.commit_pins()

    def mouseDoubleClickEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        """Remove the pin.

        Args:
            event (QtWidgets.QGraphicsSceneMouseEvent): event.
        """
        self._link.remove_pin(self)
        event.accept()
