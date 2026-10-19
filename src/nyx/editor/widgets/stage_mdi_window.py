import logging
import typing

from PySide6 import QtCore, QtWidgets

if typing.TYPE_CHECKING:
    pass


LOGGER = logging.getLogger(__name__)


class StageMdiSubWindow(QtWidgets.QMdiSubWindow):
    """MDI sub-window deleted when closed."""

    def __init__(self, parent=None):
        """Initialize StageMdiSubWindow.

        Args:
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
