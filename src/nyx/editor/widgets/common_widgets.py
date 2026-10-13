from PySide6 import QtCore, QtWidgets, QtGui


class ElidedTextLabel(QtWidgets.QLabel):
    """QLabel that elides with '...' rather than forcing the window wider."""

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self._full_text = ""
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Preferred
        )

    def set_full_text(self, full_text: str) -> None:
        self._full_text = full_text
        self.setToolTip(full_text)
        self._refresh_elided_text()

    def resizeEvent(self, resize_event) -> None:
        super().resizeEvent(resize_event)
        self._refresh_elided_text()

    def _refresh_elided_text(self) -> None:
        self.setText(
            self.fontMetrics().elidedText(
                self._full_text, QtCore.Qt.TextElideMode.ElideRight, self.width()
            )
        )


class ClickableHeaderWidget(QtWidgets.QWidget):
    clicked = QtCore.Signal()

    def mousePressEvent(self, mouse_event: QtGui.QMouseEvent) -> None:
        if mouse_event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(mouse_event)
