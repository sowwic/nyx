from PySide6 import QtCore, QtGui, QtWidgets

from .stage_mdi_window import StageMdiSubWindow
from ..graphics.painters.placeholder import PlaceholderPainter


class StageMdiArea(QtWidgets.QMdiArea):
    """Tabbed MDI area holding the stage editors, with a placeholder when empty."""

    def __init__(self, parent=None):
        """Initialize StageMdiArea.

        Args:
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(parent)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.setViewMode(QtWidgets.QMdiArea.TabbedView)
        self.setDocumentMode(True)
        self.setTabsMovable(True)
        self.setTabsClosable(True)
        self.setBackground(self.palette().brush(QtGui.QPalette.ColorRole.Window))

        self._placeholder_painter = PlaceholderPainter(
            title="No stage open", hint="File -> New Stage or Open Stage to get started"
        )

        self.subWindowActivated.connect(lambda *_: self.viewport().update())

    def addSubWindow(self, widget: QtWidgets.QWidget, flags=QtCore.Qt.WindowFlags()):
        """Wrap a widget in a stage sub-window and add it.

        Args:
            widget (QtWidgets.QWidget): editor widget.
            flags (QtCore.Qt.WindowFlags): window flags.

        Returns:
            QtWidgets.QMdiSubWindow: added sub-window.
        """
        sub_window = StageMdiSubWindow()
        sub_window.setWidget(widget)
        sub_window = super().addSubWindow(sub_window, flags)
        return sub_window

    def paintEvent(self, event):
        """Paint the placeholder when no stage is open.

        Args:
            event (QtGui.QPaintEvent): event.
        """
        super().paintEvent(event)
        if not self.subWindowList():
            self._placeholder_painter.paint(self, target=self.viewport())
