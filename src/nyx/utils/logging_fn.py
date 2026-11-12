import enum
import logging
import logging.handlers
import datetime

from PySide6 import QtCore


class LogFormat(enum.Enum):
    """Enum of log format strings."""

    minimal = "[%(levelname)s] %(message)s"
    basic = "[%(levelname)s][%(name)s] %(message)s"
    verbose = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


class QSignaler(QtCore.QObject):
    """Holder of the Qt signals emitted for logged records.

    Attributes:
        message_logged: emitted with the formatted message
        record_logged: emitted with the log record
    """

    message_logged = QtCore.Signal(str)
    record_logged = QtCore.Signal(logging.LogRecord)


class QSignalHandler(logging.Handler):
    """Logging handler forwarding records through Qt signals."""

    def __init__(self, *args, **kwargs):
        """Initialize QSignalHandler.

        Args:
            *args: forwarded to logging.Handler.
            **kwargs: forwarded to logging.Handler.
        """
        super().__init__(*args, **kwargs)
        self.emitter = QSignaler()

    def emit(self, record: logging.LogRecord):
        """Emit the record and its formatted message as signals.

        Args:
            record (logging.LogRecord): record to emit.
        """
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
    """Attach a signal handler to a logger, once.

    Args:
        logger (logging.Logger): logger to attach to.
        formatter (LogFormat | logging.Formatter): message formatter.

    Returns:
        QSignalHandler: handler attached to the logger.
    """
    if hasattr(logger, "signal_handler"):
        return logger.signal_handler

    if isinstance(formatter, LogFormat):
        formatter = logging.Formatter(formatter.value)

    signal_handler = QSignalHandler()
    signal_handler.setFormatter(formatter)
    logger.addHandler(signal_handler)
    logger.signal_handler = signal_handler
    return signal_handler


def format_log_record_timestamp(log_record: logging.LogRecord) -> str:
    """Format the creation time of a record.

    Args:
        log_record (logging.LogRecord): record.

    Returns:
        str: time as HH:MM:SS.
    """
    return datetime.datetime.fromtimestamp(log_record.created).strftime("%H:%M:%S")


def format_log_record_message_as_single_line(log_record: logging.LogRecord) -> str:
    """Get the record message with line breaks replaced by spaces.

    Args:
        log_record (logging.LogRecord): record.

    Returns:
        str: single line message.
    """
    # getMessage() always works, whereas `record.message` only exists after a
    # logging.Formatter has processed the record.
    return log_record.getMessage().replace("\r\n", " ").replace("\n", " ")
