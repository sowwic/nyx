from PySide6 import QtCore, QtGui, QtWidgets

from .stage_mdi_window import StageMdiSubWindow
from ..graphics.painters.placeholder import PlaceholderPainter


class StageMdiArea(QtWidgets.QMdiArea):
    def __init__(self, parent=None):
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
        sub_window = StageMdiSubWindow()
        sub_window.setWidget(widget)
        sub_window = super().addSubWindow(sub_window, flags)
        return sub_window

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.subWindowList():
            self._placeholder_painter.paint(self, target=self.viewport())
