import logging
import sys

from PySide6 import QtGui, QtWidgets, QtQml

import nyx.resources.resources_rc  # noqa: F401
from nyx.core.layered_config import NyxConfig
from nyx.core.session import NyxSession
from nyx.core.plugin_subsystem.registry import NYX_REGISTRY
from nyx.api.v1 import NyxPluginManager
from nyx.editor.main_window import NyxEditorMainWindow
from nyx.editor.core.actions import register_default_actions
from nyx.utils import pyside_fn
from nyx.version import __version__

LOGGER = logging.getLogger(__name__)


class NyxApplication(QtWidgets.QApplication):
    def __init__(self, initialize_plugins=True) -> None:
        super().__init__(sys.argv)
        self._session = NyxSession()
        self._plugin_manager = NyxPluginManager()
        self.setApplicationDisplayName("Nyx")
        self.setWindowIcon(QtGui.QIcon(":/icons/nyx"))
        self.setApplicationVersion(__version__)
        LOGGER.setLevel(self.config.values.logging_level)

        if initialize_plugins:
            self._plugin_manager.initialize_plugins()

    @property
    def session(self) -> NyxSession:
        return self._session

    @property
    def config(self) -> NyxConfig:
        return self._session.config

    def reset_config(self):
        """Reset application config."""
        self.config.reset()


class NyxEditorApplication(NyxApplication):
    def __init__(self) -> None:
        super().__init__()
        if self.config.values.editor_style.dark_mode:
            pyside_fn.set_dark_fusion_palette(self)

        self._load_resources()
        register_default_actions()
        self._setup_qml_engine()

        NyxEditorMainWindow.display()
        if self.config.values.editor_behaviour.new_stage_on_launch:
            self.main_window().on_stage_new()

    def main_window(self) -> NyxEditorMainWindow:
        return NyxEditorMainWindow.instance()

    @property
    def qml_engine(self):
        return self._qml_engine

    def _load_resources(self):
        """Load additional resources"""
        QtGui.QFontDatabase.addApplicationFont(":/fonts/zed-mono.ttf")

    def _setup_qml_engine(self):
        self._qml_engine = QtQml.QQmlEngine(self)
        self.sync_qml_import_paths()

    def sync_qml_import_paths(self):
        """Add any registry import roots the engine doesn't know about yet."""
        already_known_import_paths = set(self._qml_engine.importPathList())
        for import_root_directory in NYX_REGISTRY.qml_import_root_directories:
            import_root_path_text = str(import_root_directory)
            if import_root_path_text not in already_known_import_paths:
                self._qml_engine.addImportPath(import_root_path_text)
