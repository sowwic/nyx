from PySide6 import QtCore, QtGui, QtWidgets

from nyx.editor.graphics.graphics_util_object import GraphicsUtilObject
from nyx.static.enums import CoreGraphicsObjects
from nyx.editor.graphics.level_of_detail import LevelOfDetail


class GraphicsNote(GraphicsUtilObject):
    """Sticky note showing the text of a `NoteObject`."""

    RADIUS = 6.0
    PADDING = 8.0
    Z_VALUE = 0.5
    FONT = QtGui.QFont("Zed Mono", 10)

    @classmethod
    def get_type_id(cls) -> str:
        """str: id the graphics object is registered with."""
        return CoreGraphicsObjects.NOTE

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionGraphicsItem,
        widget: QtWidgets.QWidget | None = None,
    ) -> None:
        """Draw the note and its text.

        Args:
            painter (QtGui.QPainter): painter.
            option (QtWidgets.QStyleOptionGraphicsItem): style options.
            widget (QtWidgets.QWidget | None): painted widget.
        """
        lod = LevelOfDetail.from_painter(painter, text_size=self.FONT.pointSizeF())
        color = self.color
        rect = QtCore.QRectF(QtCore.QPointF(), self.item_size)
        painter.setPen(QtGui.QPen(color.darker(160), 1.0))
        painter.setBrush(color)
        painter.drawRoundedRect(rect, self.RADIUS, self.RADIUS)
        if lod.shows_text:
            painter.setPen(QtGui.QColor("#202020"))
            painter.setFont(self.FONT)
            painter.drawText(
                rect.adjusted(self.PADDING, self.PADDING, -self.PADDING, -self.PADDING),
                int(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop | QtCore.Qt.TextWordWrap),
                self.util_object.text,
            )
        self.paint_selection(painter, self.RADIUS)

    def edit(self) -> None:
        """Ask for the text of the note."""
        text, accepted = QtWidgets.QInputDialog.getMultiLineText(
            self.parent_widget(), "Note", "Text:", self.util_object.text
        )
        if accepted and text != self.util_object.text:
            self.push_properties({"text": text}, "Edit note")
