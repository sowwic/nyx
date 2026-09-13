import enum
import logging
import logging.handlers

from PySide6 import QtCore


class LogFormat(enum.Enum):
    # TODO: Move to enums module
    """Enum of log format strings."""

    minimal = "[%(levelname)s] %(message)s"
    basic = "[%(levelname)s][%(name)s] %(message)s"
    verbose = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


class QSignaler(QtCore.QObject):
    message_logged = QtCore.Signal(str)
    record_logged = QtCore.Signal(logging.LogRecord)


class QSignalHandler(logging.Handler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.emitter = QSignaler()

    def emit(self, record: logging.LogRecord):
        msg = self.format(record)
        try:
            self.emitter.record_logged.emit(record)
            self.emitter.message_logged.emit(msg)
        except RuntimeError:
            # This can happen when the application is closing and
            # the signal handler is being destroyed.
            pass


def add_signal_handler(
    logger: logging.Logger,
    formatter: LogFormat | logging.Formatter = LogFormat.minimal,
) -> QSignalHandler:
    if hasattr(logger, "signal_handler"):
        return logger.signal_handler

    if isinstance(formatter, LogFormat):
        formatter = logging.Formatter(formatter.value)

    signal_handler = QSignalHandler()
    signal_handler.setFormatter(formatter)
    logger.addHandler(signal_handler)
    logger.signal_handler = signal_handler
    return signal_handler
