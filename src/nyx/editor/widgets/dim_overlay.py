import contextlib

from PySide6 import QtCore, QtGui, QtWidgets


class DimOverlay(QtWidgets.QWidget):
    def __init__(self, target: QtWidgets.QWidget, opacity: int):
        super().__init__(target)
        self._target = target
        self._color = QtGui.QColor(0, 0, 0, opacity)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        target.installEventFilter(self)  # follow resizes
        self._sync()

    def _sync(self) -> None:
        self.setGeometry(self._target.rect())
        self.raise_()

    def eventFilter(self, obj, event) -> bool:
        if obj is self._target and event.type() == QtCore.QEvent.Type.Resize:
            self._sync()
        return super().eventFilter(obj, event)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), self._color)


@contextlib.contextmanager
def dimmed_ovelay(widget: QtWidgets.QWidget, opacity: int = 140):
    overlay = DimOverlay(target=widget, opacity=opacity)
    overlay.show()
    try:
        yield
    finally:
        overlay.hide()
        overlay.deleteLater()
