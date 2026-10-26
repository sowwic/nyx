from PySide6 import QtCore, QtGui, QtWidgets

from nyx.editor.graphics.graphics_util_object import GraphicsUtilObject
from nyx.static.enums import CoreGraphicsObjects
from nyx.editor.graphics.level_of_detail import LevelOfDetail


class GraphicsGroup(GraphicsUtilObject):
    """Titled frame of a `GroupObject`, drawn behind the nodes.

    The nodes, notes and groups inside the frame when it is pressed move along with it.
    """

    RADIUS = 10.0
    TITLE_HEIGHT = 26.0
    Z_VALUE = -3.0
    FONT = QtGui.QFont("Zed Mono", 11, QtGui.QFont.Bold)

    def __init__(self, util_object, parent=None):
        """Initialize GraphicsGroup.

        Args:
            util_object (GroupObject): group to show.
            parent (QtWidgets.QGraphicsItem | None): parent item.
        """
        self._enclosed = []
        super().__init__(util_object, parent)

    @classmethod
    def get_type_id(cls) -> str:
        """str: id the graphics object is registered with."""
        return CoreGraphicsObjects.GROUP

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionGraphicsItem,
        widget: QtWidgets.QWidget | None = None,
    ) -> None:
        """Draw the frame and the title.

        Args:
            painter (QtGui.QPainter): painter.
            option (QtWidgets.QStyleOptionGraphicsItem): style options.
            widget (QtWidgets.QWidget | None): painted widget.
        """
        lod = LevelOfDetail.from_painter(painter, text_size=self.FONT.pointSizeF())
        color = self.color
        rect = QtCore.QRectF(QtCore.QPointF(), self.item_size)
        fill = QtGui.QColor(color)
        fill.setAlpha(36)
        painter.setPen(QtGui.QPen(color, 1.5))
        painter.setBrush(fill)
        painter.drawRoundedRect(rect, self.RADIUS, self.RADIUS)

        title_fill = QtGui.QColor(color)
        title_fill.setAlpha(110)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(title_fill)
        title_rect = QtCore.QRectF(0.0, 0.0, rect.width(), self.TITLE_HEIGHT)
        painter.drawRoundedRect(title_rect, self.RADIUS, self.RADIUS)
        painter.drawRect(title_rect.adjusted(0, self.RADIUS, 0, 0))

        if lod.shows_text:
            painter.setPen(QtGui.QColor("#f2f2f2"))
            painter.setFont(self.FONT)
            painter.drawText(
                title_rect.adjusted(10.0, 0.0, -10.0, 0.0),
                int(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter),
                self.util_object.title,
            )
        self.paint_selection(painter, self.RADIUS)

    def edit(self) -> None:
        """Ask for the title of the group."""
        title, accepted = QtWidgets.QInputDialog.getText(
            self.parent_widget(), "Group", "Title:", text=self.util_object.title
        )
        if accepted and title != self.util_object.title:
            self.push_properties({"title": title}, "Rename group")

    def enclosed_items(self) -> list[QtWidgets.QGraphicsItem]:
        """Find the nodes, notes and groups inside the frame that are not selected.

        Selected items move on their own with the selection.

        Returns:
            list[QtWidgets.QGraphicsItem]: node and util object items fully inside
                the frame.
        """
        gr_stage = self.gr_stage
        if gr_stage is None:
            return []
        frame = QtCore.QRectF(self.pos(), self.item_size)
        candidates = [
            (gr_node, QtCore.QSizeF(gr_node.width, gr_node.height))
            for gr_node in gr_stage.gr_nodes()
        ] + [
            (gr_util, gr_util.item_size)
            for gr_util in gr_stage.gr_util_objects()
            if gr_util is not self
        ]
        return [
            item
            for item, size in candidates
            if not item.isSelected() and frame.contains(QtCore.QRectF(item.pos(), size))
        ]

    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        """Remember the items inside the frame, they move with it.

        The items are collected after the press is handled: it replaces the selection,
        and an item that was selected before only moves on its own if it still is.

        Args:
            event (QtWidgets.QGraphicsSceneMouseEvent): event.
        """
        super().mousePressEvent(event)
        grip = self.handle_rect.contains(event.pos())
        if event.button() == QtCore.Qt.LeftButton and not grip and self.is_editable:
            self._enclosed = self.enclosed_items()

    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        """Stop carrying the items inside the frame, and push the move.

        Args:
            event (QtWidgets.QGraphicsSceneMouseEvent): event.
        """
        super().mouseReleaseEvent(event)
        self._enclosed = []

    def itemChange(self, change, value):
        """Move the enclosed items by the distance the frame moves.

        Args:
            change (QtWidgets.QGraphicsItem.GraphicsItemChange): kind of change.
            value (typing.Any): new value.

        Returns:
            typing.Any: value to apply.
        """
        if (
            change == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemPositionChange
            and self._enclosed
        ):
            delta = value - self.pos()
            for item in self._enclosed:
                item.setPos(item.pos() + delta)
        return super().itemChange(change, value)
