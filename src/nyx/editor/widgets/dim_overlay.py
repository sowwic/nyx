import contextlib

from PySide6 import QtCore, QtGui, QtWidgets


class DimOverlay(QtWidgets.QWidget):
    """Translucent black overlay covering a widget."""

    def __init__(self, target: QtWidgets.QWidget, opacity: int):
        """Initialize DimOverlay.

        Args:
            target (QtWidgets.QWidget): widget to cover. The overlay follows its size.
            opacity (int): overlay alpha, 0-255.
        """
        super().__init__(target)
        self._target = target
        self._color = QtGui.QColor(0, 0, 0, opacity)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        target.installEventFilter(self)  # follow resizes
        self._sync()

    def _sync(self) -> None:
        """Match the geometry of the target and raise above it."""
        self.setGeometry(self._target.rect())
        self.raise_()

    def eventFilter(self, obj, event) -> bool:
        """Resize the overlay when the target is resized.

        Args:
            obj (QtCore.QObject): watched object.
            event (QtCore.QEvent): event.

        Returns:
            bool: whether the event was handled.
        """
        if obj is self._target and event.type() == QtCore.QEvent.Type.Resize:
            self._sync()
        return super().eventFilter(obj, event)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        """Fill the overlay with its color.

        Args:
            event (QtGui.QPaintEvent): event.
        """
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), self._color)


@contextlib.contextmanager
def dimmed_ovelay(widget: QtWidgets.QWidget, opacity: int = 140):
    """Dim a widget within a context.

    Args:
        widget (QtWidgets.QWidget): widget to dim.
        opacity (int): overlay alpha, 0-255.

    Yields:
        None: while the overlay is shown.
    """
    overlay = DimOverlay(target=widget, opacity=opacity)
    overlay.show()
    try:
        yield
    finally:
        overlay.hide()
        overlay.deleteLater()
