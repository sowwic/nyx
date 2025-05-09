import logging
import logging.handlers
import enum
from PySide6 import QtCore

from nyx.utils import file_fn

MAIN_LOGGER_NAME = "nyx"
LOGS_DIRECTORY = file_fn.get_nyx_data_dir() / "logs"


class LogFormat(enum.Enum):
    """Enum of log format strings."""
    minimal: str = "[%(levelname)s] %(message)s"
    basic: str = "[%(levelname)s][%(name)s] %(message)s"
    verbose: str = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


class QSignaler(QtCore.QObject):
    message_logged = QtCore.Signal(str)
    record_logged = QtCore.Signal(logging.LogRecord)


class QSignalHandler(logging.Handler):
    def __init__(self, *args, **kwargs):
        super(QSignalHandler, self).__init__(*args, **kwargs)
        self.emitter = QSignaler()

    def emit(self, record: logging.LogRecord):
        msg = self.format(record)
        self.emitter.record_logged.emit(record)
        self.emitter.message_logged.emit(msg)


def logger_exists(name: str):
    """Check if logger with given name exists.

    Args:
        name (str): logger name.

    Returns:
        bool: logger exists.
    """
    return name in logging.Logger.manager.loggerDict.keys()


def get_logger(name: str,
               level: int = logging.DEBUG,
               file_level: int = logging.ERROR,
               file_name: str = f"{MAIN_LOGGER_NAME}.log",
               std_format: str = LogFormat.basic.value,
               file_format: str = LogFormat.verbose.value):
    """Get logger object.

    Args:
        name (str): logger name.
        level (int, optional): logging level. Defaults to logging.DEBUG.
        file_level (int, optional): logging level for file handler. Defaults to logging.ERROR.
        file_name (str, optional): base logging file name. Defaults to const.MAIN_LOGGER_NAME.
        std_format (str, optional): logging format string for stream handler. Defaults to LogFormat.basic.value.
        file_format (str, optional): logging format string for file handler. Defaults to LogFormat.verbose.value.

    Returns:
        logging.Logger: logger object with given name.
    """
    if logger_exists(name):
        logger = logging.getLogger(name)
        return logger
    # Setup new logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    std_handler = logging.StreamHandler()
    logger.addHandler(std_handler)
    # Formatting
    if isinstance(std_format, LogFormat):
        std_format = std_format.value
    std_formatter = logging.Formatter(std_format)
    std_handler.setFormatter(std_formatter)
    # File output
    if file_name:
        handler_exists = any([isinstance(handler, logging.handlers.RotatingFileHandler)
                             for handler in logger.handlers])
        if not handler_exists:
            try:
                LOGS_DIRECTORY.mkdir(exist_ok=True)
                log_file_path = LOGS_DIRECTORY / file_name
                file_handler = logging.handlers.TimedRotatingFileHandler(
                    log_file_path, when="midnight", interval=1)
                file_handler.suffix = "%Y%m%d.log"
                file_handler.setLevel(file_level)
                file_formatter = logging.Formatter(file_format)
                file_handler.setFormatter(file_formatter)
                logger.addHandler(file_handler)
                logger.info(f"Log file: {log_file_path}")
            except Exception:
                logger.warning(
                    f"Unable to create filehandler for logger: {name}")
    return logger


def get_log_file_path(logger: logging.Logger, handler_type=logging.FileHandler):
    file_handler = next(iter(
        [handler for handler in logger.handlers if isinstance(handler, handler_type)]), None)
    if not file_handler:
        return None
    return file_handler.baseFilename


def get_main_logger():
    """Get main nyx logger.

    Returns:
        logging.Logger: nyx logger.
    """
    logger = get_logger(MAIN_LOGGER_NAME)
    return logger


def get_log_files(pattern: str = "*"):
    """_summary_

    Args:
        pattern (str, optional): expression match pattern. Defaults to "*".

    Returns:
        Generator[pathlib.Path]: generator for paths matching given pattern.
    """
    return LOGS_DIRECTORY.glob(pattern)


def add_signal_handler(logger: logging.Logger,
                       formatter: "LogFormat | logging.Formatter" = LogFormat.minimal) -> QSignalHandler:
    if hasattr(logger, "signal_handler"):
        return logger.signal_handler

    if isinstance(formatter, LogFormat):
        formatter = logging.Formatter(formatter.value)

    signal_handler = QSignalHandler()
    signal_handler.setFormatter(formatter)
    logger.addHandler(signal_handler)
    logger.signal_handler = signal_handler
    return signal_handler
