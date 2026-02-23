import typing
import logging
from PySide6 import QtCore
from PySide6 import QtWidgets
from PySide6 import QtGui

from nyx.core.config import Config
from nyx.utils import logging_fn
from nyx.utils import pyside_fn

if typing.TYPE_CHECKING:
    from nyx.editor.main_window import NyxEditorMainWindow


class RichLogMessageItem(QtWidgets.QListWidgetItem):
    def __init__(
        self,
        log_record: logging_fn.logging.LogRecord,
        listview: QtWidgets.QListWidget = None,
    ) -> None:
        self._icon_error = None
        self._icon_warning = None
        self._icon_info = None
        self._icon_debug = None
        self.main_window: NyxEditorMainWindow = pyside_fn.find_nyx_editor_window()
        self.level_icon_map = {
            "DEBUG": self.icon_debug,
            "INFO": self.icon_info,
            "WARNING": self.icon_warning,
            "ERROR": self.icon_error,
            "CRITICAL": self.icon_error,
        }

        self.log_record = log_record

        super().__init__(self.log_record.message, listview)
        self.setToolTip(self.log_record.message)
        self.setIcon(self.level_icon_map.get(self.log_record.levelname, self.icon_info))
        self.setSizeHint(QtCore.QSize(self.sizeHint().width(), 20))

    @property
    def icon_error(self):
        if self._icon_error:
            return self._icon_error
        pixmap = QtWidgets.QStyle.SP_MessageBoxCritical
        self._icon_error = self.main_window.style().standardIcon(pixmap)
        return self._icon_error

    @property
    def icon_warning(self):
        if self._icon_warning:
            return self._icon_warning
        pixmap = QtWidgets.QStyle.SP_MessageBoxWarning
        self._icon_warning = self.main_window.style().standardIcon(pixmap)
        return self._icon_warning

    @property
    def icon_info(self):
        if self._icon_info:
            return self._icon_info
        pixmap = QtWidgets.QStyle.SP_MessageBoxInformation
        self._icon_info = self.main_window.style().standardIcon(pixmap)
        return self._icon_info

    @property
    def icon_debug(self):
        if self._icon_debug:
            return self._icon_debug
        pixmap = QtWidgets.QStyle.SP_DialogHelpButton
        self._icon_debug = self.main_window.style().standardIcon(pixmap)
        return self._icon_debug


class LoggerWidget(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self.create_actions()
        self.create_widgets()
        self.create_layouts()
        self.create_connections()
        self._logger = self.set_logger()

    def create_actions(self):
        pass

    def create_widgets(self):
        self.std_out = QtWidgets.QTextEdit()
        self.std_out.setReadOnly(True)
        self.std_out.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.rich_out = QtWidgets.QListWidget()
        self.rich_out.setWordWrap(False)
        self.rich_out.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        self.tab_widget = QtWidgets.QTabWidget()
        self.tab_widget.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        self.tab_widget.addTab(self.rich_out, "Rich")
        self.tab_widget.addTab(self.std_out, "Raw")

    def create_layouts(self):
        self.main_layout = QtWidgets.QVBoxLayout()
        self.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)
        self.main_layout.addWidget(self.tab_widget)

    def create_connections(self):
        self.std_out.customContextMenuRequested.connect(
            self.show_raw_output_context_menu
        )
        self.rich_out.customContextMenuRequested.connect(
            self.show_rich_output_context_menu
        )

    @property
    def logger(self):
        return self._logger

    @property
    def config(self):
        return Config.load()

    @property
    def auto_scroll(self):
        return self.config.logger_autoscroll

    def set_logger(self):
        self._logger = logging.getLogger()
        logging_fn.add_signal_handler(self._logger)
        self._logger.signal_handler.emitter.message_logged.connect(
            self.append_raw_message
        )
        self._logger.signal_handler.emitter.record_logged.connect(
            self.append_rich_message
        )

    def append_raw_message(self, text: str):
        self.std_out.append(text)
        if self.auto_scroll:
            self.std_out.verticalScrollBar().setValue(
                self.std_out.verticalScrollBar().maximum()
            )

    def append_rich_message(self, record: logging_fn.logging.LogRecord):
        log_item = RichLogMessageItem(record)
        self.rich_out.addItem(log_item)
        if self.auto_scroll:
            self.rich_out.scrollToBottom()

    def show_raw_output_context_menu(self, point: QtCore.QPoint):
        menu = QtWidgets.QMenu(self.std_out)
        clear_action = QtGui.QAction("Clear", self.std_out)
        clear_action.triggered.connect(self.std_out.clear)
        menu.addAction(clear_action)
        menu.exec_(self.std_out.mapToGlobal(point))

    def show_rich_output_context_menu(self, point: QtCore.QPoint):
        menu = QtWidgets.QMenu(self.rich_out)
        clear_action = QtGui.QAction("Clear", self.rich_out)
        clear_action.triggered.connect(self.rich_out.clear)
        menu.addAction(clear_action)
        menu.exec_(self.rich_out.mapToGlobal(point))
