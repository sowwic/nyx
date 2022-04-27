import os
import sys
from PySide2 import QtWidgets

from nyx import get_main_logger
from nyx.core.config import Config
from nyx.editor.main_window import NyxEditorMainWindow

os.environ["QT_MAC_WANTS_LAYER"] = "1"
LOGGER = get_main_logger()


class NyxApplication(QtWidgets.QApplication):
    def __init__(self) -> None:
        super().__init__(sys.argv)
        self.config = Config.load()
        LOGGER.setLevel(self.config.logging_level)

    def reset_config(self):
        """Reset application config."""
        self.config = self.config.reset()


class NyxEditorApplication(NyxApplication):
    def __init__(self) -> None:
        super().__init__()
        self.main_window = NyxEditorMainWindow()
        self.main_window.show()
