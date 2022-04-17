import logging
import logging.handlers
import enum

from nyx.utils import file_fn

MAIN_LOGGER_NAME = "nyx"
LOGS_DIRECTORY = file_fn.get_data_dir() / "nyx" / "logs"


class LogFormat(enum.Enum):
    """Enum of log format strings."""
    minimal: str = "[%(levelname)s] %(message)s"
    basic: str = "[%(levelname)s][%(name)s] %(message)s"
    verbose: str = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


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
                file_hander = logging.handlers.TimedRotatingFileHandler(
                    log_file_path, when="midnight", interval=1)
                file_hander.suffix = "%Y%m%d.log"
                file_hander.setLevel(file_level)
                file_formatter = logging.Formatter(file_format)
                file_hander.setFormatter(file_formatter)
                logger.addHandler(file_hander)
            except Exception:
                logger.warning(f"Unable to create filehandler for logger: {name}")
    return logger


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
