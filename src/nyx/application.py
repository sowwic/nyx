import logging
import sys

from PySide6 import QtGui, QtWidgets

import nyx.resources.resources_rc  # noqa: F401
from nyx.core.layered_config import NyxConfig
from nyx.editor.main_window import NyxEditorMainWindow
from nyx.utils import pyside_fn
from nyx.version import __version__

LOGGER = logging.getLogger(__name__)


class NyxApplication(QtWidgets.QApplication):
    def __init__(self) -> None:
        super().__init__(sys.argv)
        self._config = NyxConfig()
        self._config.resolve()
        self._load_resources()
        self.setApplicationDisplayName("Nyx")
        self.setWindowIcon(QtGui.QIcon(":/icons/nyx"))
        self.setApplicationVersion(__version__)
        LOGGER.setLevel(self.config.values.logging_level)

    @property
    def config(self) -> NyxConfig:
        return self._config

    def reset_config(self):
        """Reset application config."""
        self.config.reset()

    def _load_resources(self):
        """Load additional resources"""
        QtGui.QFontDatabase.addApplicationFont(":/fonts/zed-mono.ttf")


class NyxEditorApplication(NyxApplication):
    def __init__(self) -> None:
        super().__init__()
        if self.config.values.editor_style.dark_mode:
            pyside_fn.set_dark_fusion_palette(self)

        NyxEditorMainWindow.display()
        self.main_window().on_stage_new()

    def main_window(self):
        return NyxEditorMainWindow.instance()
