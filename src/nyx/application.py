import logging
import os
import sys

from PySide6 import QtGui, QtWidgets, QtQml, QtQuickControls2

import nyx.resources.resources_rc  # noqa: F401
from nyx.core.layered_config import NyxConfig
from nyx.core.session import NyxSession
from nyx.core.plugin_subsystem.plugin_manager import NyxPluginManager
from nyx.core.plugin_subsystem.registry import NYX_REGISTRY
from nyx.static.env_file import load_env_file
from nyx.editor.main_window import NyxEditorMainWindow
from nyx.editor.widgets.startup_splash import NyxStartupSplash
from nyx.editor.core.actions import register_default_actions
from nyx.editor.graphics.graphics_factory import register_builtin_graphics_objects
from nyx.utils import app_icon, logging_fn, pyside_fn
from nyx.version import __version__

LOGGER = logging.getLogger(__name__)


class NyxApplication(QtWidgets.QApplication):
    """Qt application owning the session (config, stages) and plugin manager."""

    def __init__(self, initialize_plugins=True) -> None:
        """Initialize NyxApplication.

        Args:
            initialize_plugins (bool): load registered plugins on startup.
        """
        super().__init__(sys.argv)
        self._session = NyxSession()
        self.apply_config_environment()  # plugin discovery reads NYX_PLUGIN_PATH
        self._plugin_manager = NyxPluginManager()
        self.aboutToQuit.connect(self._session.shutdown)
        self.setApplicationDisplayName("Nyx")
        self.setWindowIcon(self._create_application_icon())
        self.setApplicationVersion(__version__)
        LOGGER.setLevel(self.config.values.logging_level)

        self.register_builtin_content()
        self.pre_initialize()
        if initialize_plugins:
            self._plugin_manager.initialize_plugins()
        self.post_initialize()

    @staticmethod
    def _create_application_icon() -> QtGui.QIcon:
        """Create the application icon, with the margin macOS expects in the Dock."""
        image = QtGui.QImage(":/icons/nyx.png")
        if sys.platform == "darwin":
            image = app_icon.pad_for_macos(image)
        return QtGui.QIcon(QtGui.QPixmap.fromImage(image))

    def pre_initialize(self) -> None:
        """Hook run after the builtin content is registered, before plugins load."""

    def post_initialize(self) -> None:
        """Hook run after the plugins are loaded, the last step of the startup."""

    def register_builtin_content(self) -> None:
        """Register what the application provides itself, before plugins are loaded.

        Plugins are registered after it, so a plugin can't take an id of the
        application. Nothing in the base application, the editor adds its own.
        """

    @property
    def session(self) -> NyxSession:
        """NyxSession: backend state shared by the editor."""
        return self._session

    @property
    def config(self) -> NyxConfig:
        """NyxConfig: layered application config, owned by the session."""
        return self._session.config

    def apply_config_environment(self) -> None:
        """Set the environment variables of the config in this process.

        The source file is loaded first, then the overrides, so they win over it. Values
        are expanded with the current environment, so `$PATH` can be extended. Variables
        removed from the config are left as they are.
        """
        environment = self.config.values.environment
        if environment.source_file:
            try:
                load_env_file(environment.source_file)
            except OSError as err:
                LOGGER.error(
                    "Could not read the environment file %s: %s",
                    environment.source_file,
                    err,
                )
        for name, value in environment.vars_overrides.items():
            if not name or "=" in name:
                LOGGER.warning("Invalid environment variable name: %r", name)
                continue
            os.environ[name] = os.path.expandvars(value)

    def reset_config(self):
        """Reset application config."""
        self.config.reset()


class NyxEditorApplication(NyxApplication):
    """Nyx application with the editor UI (main window, QML engine, actions)."""

    def pre_initialize(self) -> None:
        """Apply the style and show the startup splash."""
        self._startup_splash = None
        if self.config.values.editor_style.dark_mode:
            pyside_fn.set_dark_fusion_palette(self)
        self._startup_splash = self._show_startup_splash()

    def post_initialize(self) -> None:
        """Create the QML engine and main window, then close the startup splash."""
        try:
            self._load_resources()
            register_default_actions()
            self._setup_qml_engine()

            NyxEditorMainWindow.display()
            if self.config.values.editor_behaviour.new_stage_on_launch:
                self.main_window().on_stage_new()
        finally:
            if self._startup_splash:
                self._startup_splash.finish(self.main_window())
                self._startup_splash = None

    def _show_startup_splash(self) -> NyxStartupSplash | None:
        """Show the splash on the screen the main window opens on.

        Returns:
            NyxStartupSplash | None: the shown splash, None if it is turned off or
                there is no screen to show it on.
        """
        if (
            not self.config.values.editor_behaviour.show_splash_screen
            or self.platformName() == "offscreen"
        ):
            return None

        window_config = self.config.values.main_window
        splash = NyxStartupSplash(
            pyside_fn.screen_for_window_geometry(
                window_config.position, window_config.size
            )
        )
        splash.connect_to_logger(logging_fn.add_signal_handler(logging.getLogger()))
        splash.show()
        splash.raise_()
        splash.show_log_message("Starting...")
        return splash

    def register_builtin_content(self) -> None:
        """Register the graphics objects that draw nodes, plugs and links."""
        register_builtin_graphics_objects()

    def main_window(self) -> NyxEditorMainWindow:
        """Get the editor main window.

        Returns:
            NyxEditorMainWindow: main window singleton.
        """
        return NyxEditorMainWindow.instance()

    @property
    def qml_engine(self):
        """QtQml.QQmlEngine: engine shared by all QML widgets."""
        return self._qml_engine

    def _load_resources(self):
        """Load additional resources"""
        QtGui.QFontDatabase.addApplicationFont(":/fonts/zed-mono.ttf")

    def _setup_qml_engine(self):
        """Create the shared QML engine and register plugin import paths."""
        # Native styles reject control customization; Fusion matches the widget style.
        QtQuickControls2.QQuickStyle.setStyle("Fusion")
        self._qml_engine = QtQml.QQmlEngine(self)
        self.sync_qml_import_paths()

    def sync_qml_import_paths(self):
        """Add any registry import roots the engine doesn't know about yet."""
        already_known_import_paths = set(self._qml_engine.importPathList())
        for import_root_directory in NYX_REGISTRY.qml_import_root_directories:
            import_root_path_text = str(import_root_directory)
            if import_root_path_text not in already_known_import_paths:
                self._qml_engine.addImportPath(import_root_path_text)
