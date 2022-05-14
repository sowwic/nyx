import typing
from PySide2 import QtCore
from PySide2 import QtWidgets

from nyx.utils import logging_fn

if typing.TYPE_CHECKING:
    from nyx.editor.main_window import NyxEditorMainWindow


class RichLogMessageItem(QtWidgets.QListWidgetItem):

    def __init__(self,
                 log_record: logging_fn.logging.LogRecord,
                 listview: QtWidgets.QListWidget = None) -> None:
        self.__icon_error = None
        self.__icon_warning = None
        self.__icon_info = None
        self.__icon_debug = None
        self.main_window: "NyxEditorMainWindow" = QtWidgets.QApplication.instance().main_window()
        self.level_icon_map = {"DEBUG": self.icon_debug,
                               "INFO": self.icon_info,
                               "WARNING": self.icon_warning,
                               "ERROR": self.icon_error,
                               "CRITICAL": self.icon_error}

        self.log_record = log_record

        super().__init__(self.log_record.message, listview)
        self.setToolTip(self.log_record.message)
        self.setIcon(self.level_icon_map.get(self.log_record.levelname, self.icon_info))
        self.setSizeHint(QtCore.QSize(self.sizeHint().width(), 20))

    @property
    def icon_error(self):
        if self.__icon_error:
            return self.__icon_error
        pixmap = QtWidgets.QStyle.SP_MessageBoxCritical
        self.__icon_error = self.main_window.style().standardIcon(pixmap)
        return self.__icon_error

    @property
    def icon_warning(self):
        if self.__icon_warning:
            return self.__icon_warning
        pixmap = QtWidgets.QStyle.SP_MessageBoxWarning
        self.__icon_warning = self.main_window.style().standardIcon(pixmap)
        return self.__icon_warning

    @property
    def icon_info(self):
        if self.__icon_info:
            return self.__icon_info
        pixmap = QtWidgets.QStyle.SP_MessageBoxInformation
        self.__icon_info = self.main_window.style().standardIcon(pixmap)
        return self.__icon_info

    @property
    def icon_debug(self):
        if self.__icon_debug:
            return self.__icon_debug
        pixmap = QtWidgets.QStyle.SP_DialogHelpButton
        self.__icon_debug = self.main_window.style().standardIcon(pixmap)
        return self.__icon_debug


class LoggerWidget(QtWidgets.QWidget):
    def __init__(self, logger_name=logging_fn.MAIN_LOGGER_NAME, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)

        self.create_actions()
        self.create_widgets()
        self.create_layouts()
        self.create_connections()
        self.__logger = self.set_logger(logger_name)

    def create_actions(self):
        pass

    def create_widgets(self):
        self.std_out = QtWidgets.QTextEdit()
        self.std_out.setReadOnly(True)
        self.rich_out = QtWidgets.QListWidget()
        self.rich_out.setWordWrap(False)

        self.tab_widget = QtWidgets.QTabWidget()
        self.tab_widget.setContentsMargins(0, 0, 0, 0,)
        self.tab_widget.addTab(self.rich_out, "Rich")
        self.tab_widget.addTab(self.std_out, "Raw")

    def create_layouts(self):
        self.main_layout = QtWidgets.QVBoxLayout()
        self.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)
        self.main_layout.addWidget(self.tab_widget)

    def create_connections(self):
        pass

    @property
    def logger(self):
        return self.__logger

    def set_logger(self, name: str):
        self.__logger = logging_fn.get_logger(name,
                                              level=QtWidgets.QApplication.instance().config().logging_level)
        logging_fn.add_signal_handler(self.__logger)
        self.__logger.signal_handler.emitter.message_logged.connect(self.std_out.append)
        self.__logger.signal_handler.emitter.record_logged.connect(self.append_rich_message)

    def append_rich_message(self, record: logging_fn.logging.LogRecord):
        log_item = RichLogMessageItem(record)
        self.rich_out.addItem(log_item)
