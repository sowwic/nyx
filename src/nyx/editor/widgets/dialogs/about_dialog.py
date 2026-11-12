from PySide6 import QtCore, QtGui, QtWidgets

from nyx.static import vars as nyx_vars
from nyx.version import __version__


class AboutDialog(QtWidgets.QDialog):
    """Dialog with the icon, version and author of the application."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        """Initialize AboutDialog.

        Args:
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("About Nyx")
        self.setWindowFlag(QtCore.Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setFixedSize(320, 220)

        self._create_widgets()
        self._create_layouts()

    def _create_widgets(self) -> None:
        """Create the child widgets."""
        center = QtCore.Qt.AlignmentFlag.AlignCenter

        self.icon_label = QtWidgets.QLabel(self)
        self.icon_label.setPixmap(QtGui.QIcon(":/icons/nyx/128").pixmap(64, 64))
        self.icon_label.setAlignment(center)

        self.title_label = QtWidgets.QLabel(
            f"<h2>{nyx_vars.APPLICATION_TITLE.title()}</h2>"
        )
        self.title_label.setAlignment(center)

        self.info_label = QtWidgets.QLabel(
            f"Version {__version__}<br>"
            f"Developed by {nyx_vars.AUTHOR_NAME}<br>"
            f"&copy; {nyx_vars.COPYRIGHT_YEAR}<br>"
            f'<a href="{nyx_vars.REPOSITORY_URL}">{nyx_vars.REPOSITORY_URL}</a>'
        )
        self.info_label.setAlignment(center)
        self.info_label.setOpenExternalLinks(True)

    def _create_layouts(self) -> None:
        """Create the layouts and populate them with widgets."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.icon_label)
        layout.addWidget(self.title_label)
        layout.addWidget(self.info_label)
