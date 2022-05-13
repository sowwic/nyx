from PySide2 import QtWidgets

from nyx.utils import logging_fn


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

    def create_layouts(self):
        self.main_layout = QtWidgets.QVBoxLayout()
        self.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)
        self.main_layout.addWidget(self.std_out)

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
