import logging

from PySide6 import QtWidgets, QtGui


LOGGER = logging.getLogger(__name__)


class StageMdiSubWindow(QtWidgets.QMdiSubWindow):
    def __init__(self, mdi_area: QtWidgets.QMdiArea, parent=None):
        super().__init__(parent)
        self._mdi_area = mdi_area

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if len(self._mdi_area.subWindowList()) <= 1:
            LOGGER.warning("Cannot close the last open stage window")
            event.ignore()
            return
        super().closeEvent(event)
