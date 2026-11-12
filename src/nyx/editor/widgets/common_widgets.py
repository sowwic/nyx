from PySide6 import QtCore, QtWidgets, QtGui


class ElidedTextLabel(QtWidgets.QLabel):
    """QLabel that elides with '...' rather than forcing the window wider."""

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        """Initialize ElidedTextLabel.

        Args:
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(parent)
        self._full_text = ""
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Preferred
        )

    def set_full_text(self, full_text: str) -> None:
        """Set the text, elided to fit the width. The full text is the tooltip.

        Args:
            full_text (str): text to show.
        """
        self._full_text = full_text
        self.setToolTip(full_text)
        self._refresh_elided_text()

    def resizeEvent(self, resize_event) -> None:
        """Re-elide the text for the new width.

        Args:
            resize_event (QtGui.QResizeEvent): event.
        """
        super().resizeEvent(resize_event)
        self._refresh_elided_text()

    def _refresh_elided_text(self) -> None:
        """Elide the full text to the current width."""
        self.setText(
            self.fontMetrics().elidedText(
                self._full_text, QtCore.Qt.TextElideMode.ElideRight, self.width()
            )
        )


class ClickableHeaderWidget(QtWidgets.QWidget):
    """Widget emitting `clicked` when pressed with the left mouse button.

    Attributes:
        clicked: emitted on left button press
    """

    clicked = QtCore.Signal()

    def mousePressEvent(self, mouse_event: QtGui.QMouseEvent) -> None:
        """Emit `clicked` on left button press.

        Args:
            mouse_event (QtGui.QMouseEvent): event.
        """
        if mouse_event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(mouse_event)
