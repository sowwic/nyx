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
        self.__config = Config.load()
        LOGGER.setLevel(self.config().logging_level)

    def config(self):
        return self.__config

    def reset_config(self):
        """Reset application config."""
        self.__config = self.config().reset()


class NyxEditorApplication(NyxApplication):
    def __init__(self) -> None:
        super().__init__()
        NyxEditorMainWindow.display()
        self.main_window().create_stage_node_graph()

    def main_window(self):
        return NyxEditorMainWindow.instance()
