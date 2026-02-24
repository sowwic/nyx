import sys
import logging
from PySide6 import QtGui, QtWidgets

import nyx.resources.resources_rc  # noqa: F401
from nyx.version import __version__
from nyx.core.config import Config
from nyx.editor.main_window import NyxEditorMainWindow
from nyx.utils import pyside_fn


LOGGER = logging.getLogger(__name__)


class NyxApplication(QtWidgets.QApplication):
    def __init__(self) -> None:
        super().__init__(sys.argv)
        self._load_resources()
        self.setApplicationDisplayName("Nyx")
        self.setWindowIcon(QtGui.QIcon(":/icons/nyx"))
        self.setApplicationVersion(__version__)
        self._config = Config.load()
        LOGGER.setLevel(self.config().logging_level)

    def config(self):
        return self._config

    def reset_config(self):
        """Reset application config."""
        self._config = self.config().reset()

    def _load_resources(self):
        """Load additional resources"""
        QtGui.QFontDatabase.addApplicationFont(":/fonts/zed-mono.ttf")


class NyxEditorApplication(NyxApplication):
    def __init__(self) -> None:
        super().__init__()
        if self.config().dark_mode:
            pyside_fn.set_dark_fusion_palette(self)

        NyxEditorMainWindow.display()
        self.main_window().on_stage_new()

    def main_window(self):
        return NyxEditorMainWindow.instance()
