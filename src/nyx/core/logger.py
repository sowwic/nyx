import logging
import sys

from ..static.paths import APP_DATA_DIR
from ..static.vars import DEBUG


class NyxLogger(logging.Logger):
    """Logger for nyx application."""

    LOG_FILE_PATH = str(APP_DATA_DIR / "nyx.log")
    FILE_LEVEL = logging.WARNING
    STD_OUT_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    FILE_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
    STD_HANDLER = True
    FILE_HANDLER = True

    def __init__(self, name, level=logging.INFO):
        """Initialize the HazbinLogger instance.

        Args:
            name (str): Name of the logger.
            level (int, optional): Logging level. Defaults to logging.INFO.
        """
        level = logging.DEBUG if DEBUG else level
        super().__init__(name, level)
        self.init_handlers()

    def init_handlers(self):
        """Initialize logging handlers."""
        if self.hasHandlers():
            return

        if self.STD_HANDLER:
            stream_handler = logging.StreamHandler(sys.stdout)
            stream_handler.setFormatter(logging.Formatter(self.STD_OUT_FORMAT))
            self.addHandler(stream_handler)

        if self.FILE_HANDLER:
            file_handler = logging.FileHandler(self.LOG_FILE_PATH)
            file_handler.setLevel(self.FILE_LEVEL)
            file_handler.setFormatter(logging.Formatter(self.FILE_FORMAT))
            self.addHandler(file_handler)
