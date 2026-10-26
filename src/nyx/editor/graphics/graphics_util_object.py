import typing
from uuid import UUID

from PySide6 import QtCore, QtGui, QtWidgets

from nyx.core import commands

if typing.TYPE_CHECKING:
    from nyx.core.util_object import UtilObject
    from nyx.editor.graphics.graphics_stage import GraphicsStage


class GraphicsUtilObject(QtWidgets.QGraphicsItem):
    """Base of the items drawing util objects, such as notes and groups.

    The item is a view of its util object: `refresh` re-reads everything from it. It
    can be moved and resized with the mouse, which pushes undoable commands.
    """

    COLOR_PRESETS: typing.ClassVar[dict[str, str]] = {
        "Yellow": "#e8c95a",
        "Orange": "#e8944a",
        "Red": "#d9625e",
        "Purple": "#a579d4",
        "Blue": "#5b8def",
        "Green": "#6bbf6b",
        "Gray": "#8c8c8c",
    }
    SELECTED_COLOR = QtGui.QColor("#FFA637")
    HANDLE_SIZE = 14.0
    Z_VALUE = 0.0

    def __init__(self, util_object: UtilObject, parent: QtWidgets.QGraphicsItem = None):
        """Initialize GraphicsUtilObject.

        Args:
            util_object (UtilObject): util object to show.
            parent (QtWidgets.QGraphicsItem | None): parent item.
        """
        super().__init__(parent)
        self._util_object = util_object
        self._size = QtCore.QSizeF(util_object.size)
        self._resizing = False
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(self.Z_VALUE)
        self.refresh()

    @classmethod
    def get_type_id(cls) -> str:
        """str: id the graphics object is registered with. Subclasses implement."""
        raise NotImplementedError

    # ======== Properties ========= #

    @property
    def util_object(self) -> UtilObject:
        """UtilObject: util object shown by the item."""
        return self._util_object

    @property
    def uuid(self) -> UUID:
        """UUID: uuid of the util object."""
        return self._util_object.uuid

    @property
    def gr_stage(self) -> GraphicsStage | None:
        """GraphicsStage | None: scene containing the item."""
        return self.scene()

    @property
    def is_editable(self) -> bool:
        """bool: the util object can be changed."""
        return not self._util_object.is_locked

    @property
    def color(self) -> QtGui.QColor:
        """QtGui.QColor: color of the util object."""
        color = QtGui.QColor(getattr(self._util_object, "color", ""))
        return color if color.isValid() else QtGui.QColor(self.COLOR_PRESETS["Gray"])

    @property
    def item_size(self) -> QtCore.QSizeF:
        """QtCore.QSizeF: size shown, which follows the mouse while resizing."""
        return QtCore.QSizeF(self._size)

    @property
    def handle_rect(self) -> QtCore.QRectF:
        """QtCore.QRectF: grip in the bottom right corner that resizes the item."""
        return QtCore.QRectF(
            self._size.width() - self.HANDLE_SIZE,
            self._size.height() - self.HANDLE_SIZE,
            self.HANDLE_SIZE,
            self.HANDLE_SIZE,
        )

    # ======== Refresh ========= #

    def refresh(self) -> None:
        """Re-read the state of the util object and update the item to match it."""
        self.prepareGeometryChange()
        self._size = QtCore.QSizeF(self._util_object.size)
        position = self._util_object.position
        if self.pos() != position:
            self.setPos(position)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, self.is_editable)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setToolTip(self._util_object.get_description())
        self.update()

    def edit(self) -> None:
        """Ask for new content of the util object. Subclasses implement."""

    def set_color(self, color: str) -> None:
        """Change the color of the util object through a command.

        Args:
            color (str): color name, such as "#5b8def".
        """
        if color == getattr(self._util_object, "color", None):
            return
        self.push_properties({"color": color}, "Change color")

    def push_properties(self, properties: dict[str, typing.Any], text: str) -> None:
        """Push a command changing properties of the util object.

        Args:
            properties (dict[str, typing.Any]): new properties by name.
            text (str): undo stack text.
        """
        stage = self._util_object.stage
        stage.push_command(
            commands.SetUtilObjectPropertiesCommand(
                stage, {self._util_object: properties}, text=text
            )
        )

    # ======== Painting ========= #

    def boundingRect(self) -> QtCore.QRectF:
        """QtCore.QRectF: bounds of the item, including the outline."""
        return QtCore.QRectF(
            -2.0, -2.0, self._size.width() + 4.0, self._size.height() + 4.0
        )

    def paint_selection(self, painter: QtGui.QPainter, radius: float) -> None:
        """Draw the outline of a selected item and the resize grip.

        Args:
            painter (QtGui.QPainter): painter.
            radius (float): radius of the corners of the item.
        """
        if self.isSelected():
            painter.setPen(QtGui.QPen(self.SELECTED_COLOR, 2.0))
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawRoundedRect(
                QtCore.QRectF(QtCore.QPointF(), self._size), radius, radius
            )
        if self.is_editable and (self.isSelected() or self.isUnderMouse()):
            handle = self.handle_rect.adjusted(4, 4, -2, -2)
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 160), 1.5))
            for offset in (0.0, 4.0, 8.0):
                painter.drawLine(
                    handle.right() - offset,
                    handle.bottom(),
                    handle.right(),
                    handle.bottom() - offset,
                )

    # ======== Events ========= #

    def hoverMoveEvent(self, event: QtWidgets.QGraphicsSceneHoverEvent) -> None:
        """Show the resize cursor over the grip.

        Args:
            event (QtWidgets.QGraphicsSceneHoverEvent): event.
        """
        over_handle = self.is_editable and self.handle_rect.contains(event.pos())
        self.setCursor(
            QtCore.Qt.SizeFDiagCursor if over_handle else QtCore.Qt.ArrowCursor
        )
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event: QtWidgets.QGraphicsSceneHoverEvent) -> None:
        """Redraw without the grip.

        Args:
            event (QtWidgets.QGraphicsSceneHoverEvent): event.
        """
        self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        """Start resizing when the grip is pressed.

        Args:
            event (QtWidgets.QGraphicsSceneMouseEvent): event.
        """
        if (
            event.button() == QtCore.Qt.LeftButton
            and self.is_editable
            and self.handle_rect.contains(event.pos())
        ):
            self._resizing = True
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        """Resize while the grip is dragged.

        Args:
            event (QtWidgets.QGraphicsSceneMouseEvent): event.
        """
        if not self._resizing:
            super().mouseMoveEvent(event)
            return
        min_width, min_height = self._util_object.MIN_SIZE
        self.prepareGeometryChange()
        self._size = QtCore.QSizeF(
            max(event.pos().x(), min_width), max(event.pos().y(), min_height)
        )
        self.update()

    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        """Push a command for the resize, or for the items that were moved.

        Args:
            event (QtWidgets.QGraphicsSceneMouseEvent): event.
        """
        if self._resizing:
            self._resizing = False
            size = [self._size.width(), self._size.height()]
            if size != self._util_object.serialize_properties()["size"]:
                self.push_properties({"size": size}, "Resize")
            else:
                self.refresh()
            return
        super().mouseReleaseEvent(event)
        gr_stage = self.gr_stage
        if gr_stage is not None:
            gr_stage.commit_moves()

    def mouseDoubleClickEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        """Edit the util object.

        Args:
            event (QtWidgets.QGraphicsSceneMouseEvent): event.
        """
        if self.is_editable:
            self.edit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def itemChange(self, change, value):
        """Redraw when the selection changes.

        Args:
            change (QtWidgets.QGraphicsItem.GraphicsItemChange): kind of change.
            value (typing.Any): new value.

        Returns:
            typing.Any: value to apply.
        """
        if change == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.update()
        return super().itemChange(change, value)

    def parent_widget(self) -> QtWidgets.QWidget | None:
        """QtWidgets.QWidget | None: view showing the item, to parent dialogs."""
        gr_stage = self.gr_stage
        views = gr_stage.views() if gr_stage is not None else []
        return views[0] if views else None
