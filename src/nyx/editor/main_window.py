import typing

from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets

from nyx import get_main_logger

if typing.TYPE_CHECKING:
    from nyx.core.config import Config


LOGGER = get_main_logger()


class NyxEditorMainWindow(QtWidgets.QMainWindow):

    __INSTANCE: "NyxEditorMainWindow" = None

    DEFAULT_TITLE = "Nyx Editor"
    MINIMUM_SIZE = (500, 400)

    @classmethod
    def instance(cls):
        return cls.__INSTANCE

    @classmethod
    def display(cls):
        if not cls.__INSTANCE:
            cls.__INSTANCE = cls()

        if cls.__INSTANCE.isHidden():
            cls.__INSTANCE.show()
        else:
            cls.__INSTANCE.raise_()
            cls.__INSTANCE.activateWindow()

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.DEFAULT_TITLE)
        self.setMinimumSize(*self.MINIMUM_SIZE)

        # Initialize ui
        self.create_actions()
        self.create_widgets()
        self.create_menubar()
        self.create_layouts()
        self.create_connections()

        self.apply_config_values()

    @property
    def config(self) -> "Config":
        return QtWidgets.QApplication.instance().config()

    def create_actions(self):
        pass

    def create_menubar(self):
        pass

    def create_widgets(self):
        # mdi area
        self.mdi_area = QtWidgets.QMdiArea()
        self.setCentralWidget(self.mdi_area)
        self.mdi_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.mdi_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.mdi_area.setViewMode(QtWidgets.QMdiArea.TabbedView)
        self.mdi_area.setDocumentMode(True)
        self.mdi_area.setTabsClosable(True)
        self.mdi_area.setTabsMovable(True)

        # Dock Widgets
        self.setTabPosition(QtCore.Qt.RightDockWidgetArea, QtWidgets.QTabWidget.East)
        self.setTabPosition(QtCore.Qt.LeftDockWidgetArea, QtWidgets.QTabWidget.North)

    def create_layouts(self):
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)

    def create_connections(self):
        pass

    # Events
    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        try:
            self.save_config_value()
        except Exception:
            LOGGER.exception("Failed to save config values")
        return super().closeEvent(event)

    # Config methods

    def save_config_value(self):
        self.config.window_position = (self.pos().x(), self.pos().y())
        self.config.window_size = (self.width(), self.height())
        # self.config.window_always_on_top = self.pin_window_btn.isChecked()

    def apply_config_values(self):
        """Apply values from application config."""
        self.resize(QtCore.QSize(*self.config.window_size))
        if not self.config.window_position:
            center_position: QtCore.QPoint = self.pos(
            ) + QtWidgets.QApplication.primaryScreen().geometry().center() - self.geometry().center()
            self.config.window_position = (center_position.x(), center_position.y())
        self.move(QtCore.QPoint(*self.config.window_position))

        # TODO: add always on top toggle
        # self.toggle_always_on_top(self.config.window_always_on_top)
        LOGGER.setLevel(self.config.logging_level)

    def reset_application_config(self):
        """Reset application config and apply changes."""
        QtWidgets.QApplication.instance().reset_config()
        self.apply_config_values()
