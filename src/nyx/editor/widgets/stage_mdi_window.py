import logging
import typing

from PySide6 import QtCore, QtWidgets, QtGui

if typing.TYPE_CHECKING:
    from ..widgets.stage_graph_editor import StageGraphEditor


LOGGER = logging.getLogger(__name__)


class StageMdiSubWindow(QtWidgets.QMdiSubWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
