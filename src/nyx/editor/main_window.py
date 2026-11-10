from __future__ import annotations

import functools
import pathlib
import typing
import logging
import base64

import shiboken6
from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

from ..version import __version__
from nyx.editor.core.action_registry import ACTION_REGISTRY
from nyx.editor.core.action_router import ACTION_ROUTER
from nyx.editor.core.actions import ActionId
from .views.stage_graph_debug_overlay import StageGraphDebugOverlay
from .views.stage_tree_view import StageTreeView
from .views.nodes_palette_view import NodesPaletteView
from .widgets.stage_graph_editor import StageGraphEditor
from .widgets.bridge_panel import BridgePanel
from .widgets.notifications import NotificationManager
from .widgets.dialogs.execution_progress_dialog import ExecutionProgressDialog
from .widgets.output_log.output_log_dock import OutputLogDockWidget
from .widgets.inspector import Inspector
from .widgets.editor_toolbar import EditorToolBar
from .widgets import menubar_menus
from .widgets.stage_mdi_area import StageMdiArea
from ..utils import pyside_fn
from ..static.enums import EditorUIObject
from ..core.session import SESSION_FILE_SUFFIX
from ..static.paths import LAST_SESSION_FILE_PATH


if typing.TYPE_CHECKING:
    from nyx.api.v1 import Stage
    from ..application import NyxEditorApplication
    from ..core.layered_config import NyxConfig


LOGGER = logging.getLogger(__name__)


class NyxEditorMainWindow(QtWidgets.QMainWindow):
    """Main window of the Nyx editor: docks, menus and the MDI area of stage editors."""

    _INSTANCE: NyxEditorMainWindow = None

    DEFAULT_TITLE = f"Nyx Editor v{__version__}"
    LAYOUT_VERSION = 2
    MINIMUM_SIZE = (1000, 600)

    @classmethod
    def instance(cls):
        """Get the window singleton.

        Returns:
            NyxEditorMainWindow | None: window, None if not displayed yet.
        """
        return cls._INSTANCE

    @classmethod
    def display(cls):
        """Create the window singleton if needed and show it."""
        if not cls._INSTANCE:
            cls._INSTANCE = cls()

        if cls._INSTANCE.isHidden():
            cls._INSTANCE.show()
        else:
            cls._INSTANCE.raise_()
            cls._INSTANCE.activateWindow()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        """Initialize NyxEditorMainWindow.

        Args:
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(parent)
        self._has_completed_first_show = False
        self._dock_widgets: list[QtWidgets.QDockWidget] = []
        self._is_nyx_editor_window = True
        self.setWindowTitle(self.DEFAULT_TITLE)
        self.setMinimumSize(*self.MINIMUM_SIZE)
        self.setDockNestingEnabled(True)
        self.setDockOptions(
            self.dockOptions() | QtWidgets.QMainWindow.DockOption.AllowTabbedDocks
        )

        self.undo_group = QtGui.QUndoGroup(self)
        self.viewport_debug_overlay = StageGraphDebugOverlay()

        # Initialize ui
        self.create_actions()
        self.create_widgets()
        self._create_dock_widgets()
        self.create_menubar()
        self.create_layouts()
        self.create_connections()

        self.apply_config_values()
        NotificationManager.set_host(self)

    @property
    def config(self) -> NyxConfig:
        """NyxConfig: application config."""
        return self.application.session.config

    @property
    def current_stage_graph(self) -> StageGraphEditor | None:
        """StageGraphEditor | None: editor of the active window."""
        if not self.current_mdi_window:
            return None
        return self.current_mdi_window.widget()

    @property
    def current_mdi_window(self) -> QtWidgets.QMdiSubWindow | None:
        """QtWidgets.QMdiSubWindow | None: active MDI window."""
        return self.mdi_area.currentSubWindow()

    @property
    def application(self):
        """NyxEditorApplication: running application."""
        app: NyxEditorApplication = QtWidgets.QApplication.instance()
        return app

    @property
    def dock_widgets(self) -> list[QtWidgets.QDockWidget]:
        """list[QtWidgets.QDockWidget]: docks created by the window."""
        return self._dock_widgets

    def _create_dock(
        self,
        title: str,
        object_name: str,
        widget: QtWidgets.QWidget,
        dock_class: type[QtWidgets.QDockWidget] | None = None,
        allowed_areas: QtCore.Qt.DockWidgetArea | None = None,
    ) -> QtWidgets.QDockWidget:
        """Create a dock widget owned by the window.

        Args:
            title (str): dock title.
            object_name (str): object name used to save and restore the layout.
            widget (QtWidgets.QWidget): widget shown in the dock.
            dock_class (type[QtWidgets.QDockWidget] | None): dock class. Defaults to
                QDockWidget.
            allowed_areas (QtCore.Qt.DockWidgetArea | None): areas the dock can be placed
                in.

        Returns:
            QtWidgets.QDockWidget: created dock.
        """
        if dock_class is None:
            dock_class = QtWidgets.QDockWidget
        dock = dock_class(title, self)
        if widget:
            dock.setWidget(widget)
        dock.setObjectName(object_name)
        if allowed_areas is not None:
            dock.setAllowedAreas(allowed_areas)
        self._dock_widgets.append(dock)
        return dock

    def create_actions(self):
        """Register handlers of the window actions."""
        register = ACTION_ROUTER.register_handler
        register(ActionId.EXECUTE_STAGE, self.execute_stage_graph)
        register(ActionId.EXECUTE_FROM_SELECTED, self.execute_from_selected_node)
        register(ActionId.NEW_STAGE, self.on_stage_new)
        register(ActionId.OPEN_STAGE, self.on_stage_open)
        register(ActionId.OPEN_STAGE_TAB, self.on_stage_open_tabbed)
        register(ActionId.SAVE_STAGE, self.on_stage_save)
        register(ActionId.SAVE_STAGE_AS, self.on_stage_save_as)
        register(ActionId.SAVE_SESSION, self.on_session_save)
        register(ActionId.LOAD_SESSION, self.on_session_load)
        register(ActionId.RESTORE_LAST_SESSION, self.on_session_restore_last)
        register(ActionId.RESET_CONFIG, self.reset_application_config)
        # Fallbacks so toolbar buttons work before the tree view has focus
        register(ActionId.CREATE_NODE, self.show_nodes_palette)
        register(
            ActionId.DELETE_NODE, lambda: self.stage_tree_view.delete_selected_node()
        )
        ACTION_REGISTRY.attach_shortcuts(self)

    def show_nodes_palette(self):
        """Show the modal nodes palette for the current stage graph."""
        if self.current_stage_graph is not None:
            self.current_stage_graph.show_nodes_palette_centered()

    def create_menubar(self):
        """Create the menu bar menus."""
        self.menubar_file_menu = menubar_menus.FileMenu(self)
        self.menubar_edit_menu = menubar_menus.EditMenu(self)
        self.menubar_session_menu = menubar_menus.SessionMenu(self)
        self.menubar_view_menu = menubar_menus.ViewMenu(self)
        self.menubar_window_menu = menubar_menus.WindowMenu(self)

        self.menuBar().setNativeMenuBar(False)
        self.menuBar().addMenu(self.menubar_file_menu)
        self.menuBar().addMenu(self.menubar_edit_menu)
        self.menuBar().addMenu(self.menubar_session_menu)
        self.menuBar().addMenu(self.menubar_view_menu)
        self.menuBar().addMenu(self.menubar_window_menu)

    def create_widgets(self):
        """Create the window widgets."""
        self.stage_tree_view = StageTreeView()
        self.inspector = Inspector(self)
        self.nodes_palette_view = NodesPaletteView(drag_enabled=True, parent=self)

        self.bridge_panel = BridgePanel(self.application.session, self)

        self.undo_view = QtWidgets.QUndoView(self.undo_group, self)
        self.undo_view.setEmptyLabel("Stage initial state")
        self.tool_bar = EditorToolBar(self)

        # mdi area
        self.mdi_area = StageMdiArea()
        self.setCentralWidget(self.mdi_area)

    def _create_dock_widgets(self):
        """Create the dock widgets and the default tab positions."""
        # Dock Widgets
        self.setTabPosition(QtCore.Qt.RightDockWidgetArea, QtWidgets.QTabWidget.East)
        self.setTabPosition(QtCore.Qt.LeftDockWidgetArea, QtWidgets.QTabWidget.West)
        self.setTabPosition(QtCore.Qt.BottomDockWidgetArea, QtWidgets.QTabWidget.North)

        self.nodes_palette_dock = self._create_dock(
            title="Nodes Palette",
            object_name=EditorUIObject.NODES_PALETTE_DOCK,
            widget=self.nodes_palette_view,
        )
        self.stage_tree_dock = self._create_dock(
            title="Tree View",
            object_name=EditorUIObject.STAGE_TREE_DOCK,
            widget=self.stage_tree_view,
        )
        self.undo_dock = self._create_dock(
            title="Undo History",
            object_name=EditorUIObject.UNDO_HISTORY_DOCK,
            widget=self.undo_view,
        )
        self.bridge_dock = self._create_dock(
            title="Bridge",
            object_name=EditorUIObject.BRIDGE_DOCK,
            widget=self.bridge_panel,
        )
        self.logger_dock: OutputLogDockWidget = self._create_dock(
            title="Output Log",
            object_name=EditorUIObject.LOG_OUTPUT_DOCK,
            widget=None,
            dock_class=OutputLogDockWidget,
            allowed_areas=QtCore.Qt.DockWidgetArea.BottomDockWidgetArea
            | QtCore.Qt.DockWidgetArea.LeftDockWidgetArea,
        )

        self.toolbar_dock = self._create_dock(
            title="Tools",
            object_name=EditorUIObject.TOOLBAR_DOCK,
            widget=self.tool_bar,
            allowed_areas=QtCore.Qt.DockWidgetArea.TopDockWidgetArea
            | QtCore.Qt.DockWidgetArea.BottomDockWidgetArea,
        )
        self.inspector_dock = self._create_dock(
            title="Inspector",
            object_name=EditorUIObject.INSPECTOR_DOCK,
            widget=self.inspector,
        )

    def _apply_default_docks_layout(self):
        """Reset the docks to the default layout."""
        # Start from a clean slate so no stale tab groups or floating state remain
        for dock in self.dock_widgets:
            dock.setFloating(False)
            self.removeDockWidget(dock)

        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.stage_tree_dock)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.undo_dock)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.bridge_dock)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.logger_dock)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.inspector_dock)
        self.addDockWidget(
            QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, self.nodes_palette_dock
        )
        self.addDockWidget(QtCore.Qt.TopDockWidgetArea, self.toolbar_dock)

        # Tabify dock widgets
        self.tabifyDockWidget(self.stage_tree_dock, self.nodes_palette_dock)
        self.tabifyDockWidget(self.stage_tree_dock, self.undo_dock)
        self.tabifyDockWidget(self.stage_tree_dock, self.bridge_dock)

        for dock in self.dock_widgets:
            dock.show()

        # Default in tabified group
        self.stage_tree_dock.raise_()

    def _apply_default_geometry(self):
        """Resize the window to most of the screen and center it."""
        screen_geometry = self.screen().availableGeometry()
        default_width = int(screen_geometry.width() * 0.8)
        default_height = int(screen_geometry.height() * 0.8)
        self.resize(default_width, default_height)
        pyside_fn.move_window_to_screen_center(self)

    def create_layouts(self):
        """Create layouts. The window has none yet."""
        pass

    def create_connections(self):
        """Connect signals."""
        self.mdi_area.subWindowActivated.connect(self.on_node_graph_window_activated)
        self.mdi_area.subWindowActivated.connect(self.update_title)
        self.undo_group.indexChanged.connect(self.update_title)
        self.undo_group.indexChanged.connect(self.inspector.update_data)
        self.inspector.setEnabled(self.current_mdi_window is not None)

    # Events
    def showEvent(self, show_event: QtGui.QShowEvent) -> None:
        """Restore the log dock height after the first show.

        Args:
            show_event (QtGui.QShowEvent): event.
        """
        super().showEvent(show_event)
        if self._has_completed_first_show:
            return
        self._has_completed_first_show = True
        # The first layout pass has not happened yet at this point, so wait one
        # event-loop turn before asking the dock to restore its height.
        QtCore.QTimer.singleShot(
            0,
            self.logger_dock.restore_expanded_height_into_main_window_if_possible,
        )

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Prompt to save each editor, then save the last session and config.

        The close is ignored if any save prompt is cancelled.

        Args:
            event (QtGui.QCloseEvent): event.
        """
        for sub_window in self.mdi_area.subWindowList():
            graph_editor: StageGraphEditor = sub_window.widget()
            result = graph_editor.maybe_save()
            if not result:
                event.ignore()
                return

        # Editors are still open here, so their scope/view state can be captured
        try:
            self.save_session(LAST_SESSION_FILE_PATH)
        except Exception:
            LOGGER.exception("Failed to save last session")
        try:
            self.save_config_value()
        except Exception:
            LOGGER.exception("Failed to save config values")
        return super().closeEvent(event)

    # Config methods
    def save_config_value(self):
        """Store window geometry and layout in the config."""
        self.config.values.main_window.position = (self.pos().x(), self.pos().y())
        self.config.values.main_window.size = (self.width(), self.height())
        self.config.values.main_window.layout.version = self.LAYOUT_VERSION
        self.config.values.main_window.layout.state = base64.b64encode(
            bytes(self.saveState(self.LAYOUT_VERSION))
        ).decode("ascii")
        # self.config.window_always_on_top = self.pin_window_btn.isChecked()
        self.logger_dock.save_config_values(self.config)

    def apply_config_values(self):
        """Apply values from application config."""
        window_config = self.config.values.main_window
        if window_config.size and window_config.position:
            self.resize(QtCore.QSize(*window_config.size))
            self.move(QtCore.QPoint(*window_config.position))
        else:
            self._apply_default_geometry()

        # TODO: add always on top toggle
        # self.toggle_always_on_top(self.config.window_always_on_top)
        LOGGER.setLevel(self.config.values.logging_level)
        self._apply_viewport_debug_overlay()
        self._apply_show_address_names()
        self._apply_stage_render_options()

        # The log dock's expansion state and size constraints must be in place
        # BEFORE the layout is built or restored. Otherwise Qt clamps the dock
        # to its collapsed/default size while placing it.
        self.logger_dock.apply_config_values(self.config)
        self._load_layout_from_config()

    def _apply_stage_render_options(self):
        """Redraw the open stages with the render options of the config.

        The background is refreshed in place. Links read their style when they are
        created and the chain highlight is chosen when the scope is built, so the
        scope is rebuilt for those.
        """
        for sub_window in self.mdi_area.subWindowList():
            graph_editor: StageGraphEditor = sub_window.widget()
            graph_editor.gr_stage.apply_render_options()
            graph_editor.gr_stage.rebuild_current_scope()

    def _load_layout_from_config(self):
        """Restore the dock layout from the config.

        Returns:
            bool: saved layout was applied, False if the default was used.
        """
        layout_config = self.config.values.main_window.layout
        if not layout_config.state or layout_config.version != self.LAYOUT_VERSION:
            LOGGER.info("No compatible saved layout, using default")
            self._apply_default_docks_layout()
            return False

        try:
            layout_state = QtCore.QByteArray(base64.b64decode(layout_config.state))
        except ValueError:
            LOGGER.info("Corrupt saved layout, using default")
            self._apply_default_docks_layout()
            return False

        if not self.restoreState(layout_state, version=layout_config.version):
            LOGGER.warning("Layout state restore failed, using default")
            self._apply_default_docks_layout()
            return False

        LOGGER.info("Using saved main window layout")
        return True

    def reset_application_config(self):
        """Reset application config and apply changes."""
        self.config.reset()
        QtCore.QTimer.singleShot(0, self.apply_config_values)

    def set_viewport_debug_overlay(self, enabled: bool):
        """Turn the debug overlay of the graph views on or off, and remember it.

        Args:
            enabled (bool): show the overlay.
        """
        self.config.values.editor_widgets.graphics_stage.viewport_debug_overlay = enabled
        self._apply_viewport_debug_overlay()

    def set_show_address_names(self, enabled: bool):
        """Show address names instead of display names in every stage, and remember it.

        Args:
            enabled (bool): show the address names.
        """
        self.application.session.set_show_address_names(enabled)
        self._apply_show_address_names()

    def _apply_show_address_names(self):
        """Show the config value of the names toggle in the menu and the stages."""
        enabled = self.application.session.show_address_names
        self.menubar_view_menu.set_show_address_names_checked(enabled)
        for stage in self.application.session.stages:
            stage.show_address_names = enabled
        # The views redraw what they show, with the names in the new form.
        for sub_window in self.mdi_area.subWindowList():
            stage_graph = sub_window.widget()
            if isinstance(stage_graph, StageGraphEditor):
                stage_graph.gr_stage.rebuild_current_scope()

    def _apply_viewport_debug_overlay(self):
        """Show the config value of the debug overlay in the menu and the views."""
        enabled = self.config.values.editor_widgets.graphics_stage.viewport_debug_overlay
        self.menubar_view_menu.set_debug_overlay_checked(enabled)
        current = self.current_stage_graph
        self.viewport_debug_overlay.attach(
            current.gr_view if enabled and current is not None else None
        )

    def create_stage_node_graph(
        self, stage: Stage | None = None, file_path: pathlib.Path | str | None = None
    ):
        """Create an editor sub-window and add it to the MDI area.

        Args:
            stage (Stage | None): stage to edit. A new one is created if omitted.
            file_path (pathlib.Path | str | None): stage file to load instead of a stage.

        Returns:
            QtWidgets.QMdiSubWindow: created sub-window.
        """
        if file_path:
            stage_graph_editor_widget = StageGraphEditor.from_json_file(file_path)
        else:
            stage_graph_editor_widget = StageGraphEditor(stage)

        mdi_sub_window = self.mdi_area.addSubWindow(stage_graph_editor_widget)

        # Connect signals
        stage_graph_editor_widget.selection_model.selectionChanged.connect(
            self.inspector.update_data
        )
        stage_graph_editor_widget.node_type_dropped.connect(
            self.nodes_palette_view.on_node_dropped
        )
        stage_graph_editor_widget.stage_file_used.connect(self.add_recent_file)
        if file_path:
            self.add_recent_file(str(file_path))
        return mdi_sub_window

    def add_recent_file(self, file_path: str):
        """Add a file to the recent files.

        Args:
            file_path (str): stage file path.
        """
        self.application.session.add_recent_file(file_path)

    def remove_recent_file(self, file_path: str):
        """Remove a file from the recent files.

        Args:
            file_path (str): stage file path.
        """
        self.application.session.remove_recent_file(file_path)

    def find_window_for_file(
        self, file_path: pathlib.Path | str
    ) -> QtWidgets.QMdiSubWindow | None:
        """Find the window editing a stage file.

        Args:
            file_path (pathlib.Path | str): stage file path.

        Returns:
            QtWidgets.QMdiSubWindow | None: window, None if the file isn't open.
        """
        stage = self.application.session.find_stage_for_file(file_path)
        if stage is None:
            return None
        for sub_wnd in self.mdi_area.subWindowList():
            if sub_wnd.widget().stage is stage:
                return sub_wnd
        return None

    def activate_editor_window(self, sub_wnd: QtWidgets.QMdiSubWindow) -> None:
        """Bring an editor window to the front and make it the active one.

        Args:
            sub_wnd (QtWidgets.QMdiSubWindow): window to activate.
        """
        if sub_wnd.isMinimized():
            sub_wnd.showNormal()
        self.mdi_area.setActiveSubWindow(sub_wnd)
        self.on_node_graph_window_activated(sub_wnd)

    def activate_window_for_file(self, file_path: pathlib.Path | str) -> bool:
        """Activate the editor already showing given file, if any."""
        sub_wnd = self.find_window_for_file(file_path)
        if sub_wnd is None:
            return False
        self.mdi_area.setActiveSubWindow(sub_wnd)
        self.on_node_graph_window_activated(sub_wnd)
        return True

    def on_stage_open_recent(self, file_path: str):
        """Open a recent file in a new window, or activate the window already showing it.

        Missing files are removed from the recent files.

        Args:
            file_path (str): stage file path.
        """
        if not pathlib.Path(file_path).is_file():
            LOGGER.warning("Recent file no longer exists: %s", file_path)
            self.remove_recent_file(file_path)
            return

        if self.activate_window_for_file(file_path):
            return

        sub_wnd = self.create_stage_node_graph()
        stage_graph: StageGraphEditor = sub_wnd.widget()

        if not stage_graph.open_stage_file(file_path):
            self.mdi_area.removeSubWindow(sub_wnd)
            return

        self.mdi_area.setActiveSubWindow(sub_wnd)
        sub_wnd.show()
        self.on_node_graph_window_activated(sub_wnd)

    # Slots
    def update_title(self):
        """Show the active stage in the window title."""
        if not self.current_stage_graph:
            self.setWindowTitle(self.DEFAULT_TITLE)
            return

        title = f"{self.DEFAULT_TITLE} - {self.current_stage_graph.windowTitle()}"
        self.setWindowTitle(title)

    @QtCore.Slot(QtWidgets.QMdiSubWindow)
    def on_node_graph_window_activated(self, mdi_window: QtWidgets.QMdiSubWindow | None):
        """Point the tree view and undo group at the activated editor.

        Args:
            mdi_window (QtWidgets.QMdiSubWindow | None): activated window, None if there
                is none.
        """
        self.inspector.setEnabled(mdi_window is not None)
        self._apply_viewport_debug_overlay()
        if mdi_window is None:
            self.stage_tree_view.set_stage(None)
            self.undo_group.setActiveStack(None)
            return

        stage_graph: StageGraphEditor = mdi_window.widget()
        self.stage_tree_view.set_stage(stage_graph.stage)
        self.undo_group.setActiveStack(stage_graph.stage.undo_stack)
        self.stage_tree_view.setSelectionModel(stage_graph.selection_model)

    def on_stage_open(self, tabbed: bool = False):
        """Ask for a stage file and open it.

        The active window is reused unless `tabbed` is set, and a file that is already
        open is activated instead.

        Args:
            tabbed (bool): open in a new window.
        """
        file_path = StageGraphEditor.pick_stage_file(self)
        if not file_path:
            return
        if self.activate_window_for_file(file_path):
            return

        created_new = tabbed or self.current_mdi_window is None
        sub_wnd = (
            self.create_stage_node_graph() if created_new else self.current_mdi_window
        )

        stage_graph: StageGraphEditor = sub_wnd.widget()
        file_opened = stage_graph.open_stage_file(file_path)

        if not file_opened:
            if created_new:
                self.mdi_area.removeSubWindow(sub_wnd)
            # else: cancelled saving into an existing window — leave it alone
            return

        self.mdi_area.setActiveSubWindow(sub_wnd)
        sub_wnd.show()
        self.on_node_graph_window_activated(sub_wnd)

    def on_session_save(self):
        """Ask for a file and save the session to it."""
        file_filter = f"Nyx Session (*{SESSION_FILE_SUFFIX})"
        file_path = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save session to file", None, file_filter
        )[0]
        if not file_path:
            return
        if not file_path.endswith(SESSION_FILE_SUFFIX):
            file_path += SESSION_FILE_SUFFIX
        self.save_session(file_path)

    def save_session(self, file_path: pathlib.Path | str):
        """Save open stages with their scope and view state, and the active stage.

        Args:
            file_path (pathlib.Path | str): session file.
        """
        current = self.current_stage_graph
        editors = {w.widget().stage: w.widget() for w in self.mdi_area.subWindowList()}
        self.application.session.save_to_file(
            file_path,
            stage_state=lambda stage: (
                editors[stage].get_session_state() if stage in editors else {}
            ),
            active_stage=current.stage if current else None,
        )

    def on_session_load(self):
        """Ask for a session file and load it."""
        file_filter = f"Nyx Session (*{SESSION_FILE_SUFFIX})"
        file_path = QtWidgets.QFileDialog.getOpenFileName(
            self, "Load session", None, file_filter
        )[0]
        if not file_path:
            return
        self.load_session(file_path)

    def on_session_restore_last(self):
        """Load the session saved when the editor last exited."""
        if not LAST_SESSION_FILE_PATH.is_file():
            LOGGER.warning("No last session to restore")
            return
        self.load_session(LAST_SESSION_FILE_PATH)

    def load_session(self, file_path: pathlib.Path | str):
        """Open the stages of a session file and restore their state.

        Stages that are already open are only activated, not changed.

        Args:
            file_path (pathlib.Path | str): session file.
        """
        try:
            data = self.application.session.read_file(file_path)
        except OSError, ValueError:
            LOGGER.exception("Failed to read session file: %s", file_path)
            return
        for entry in data["stages"]:
            stage_path = entry["path"]
            already_open = self.find_window_for_file(stage_path) is not None
            self.on_stage_open_recent(stage_path)
            sub_wnd = self.find_window_for_file(stage_path)
            if sub_wnd is None or already_open:
                continue
            editor: StageGraphEditor = sub_wnd.widget()
            editor.apply_session_state(entry)
            # The view needs its final size before it can be centered
            QtCore.QTimer.singleShot(
                0, functools.partial(self._apply_view_state, editor, entry)
            )
        if data["active"]:
            self.activate_window_for_file(data["active"])

    @staticmethod
    def _apply_view_state(editor: StageGraphEditor, entry: dict):
        """Apply the saved view state if the editor still exists.

        Args:
            editor (StageGraphEditor): editor to update.
            entry (dict): session entry holding the "view" state.
        """
        if shiboken6.isValid(editor) and "view" in entry:
            editor.gr_view.apply_view_state(entry["view"])

    def on_stage_open_tabbed(self):
        """Open a stage file in a new window."""
        self.on_stage_open(tabbed=True)

    def on_stage_new(self):
        """Open a new empty stage in a new window."""
        try:
            sub_wnd = self.create_stage_node_graph()
            sub_wnd.show()
        except Exception:
            LOGGER.exception("Failed to create new stage view window")

    def on_stage_save(self):
        """Save the active stage."""
        if self.current_stage_graph:
            self.current_stage_graph.on_stage_save()

    def on_stage_save_as(self):
        """Save the active stage to a new file."""
        if self.current_stage_graph:
            self.current_stage_graph.on_stage_save_as()

    def execute_stage_graph(self):
        """Execute the active stage."""
        if not self.current_stage_graph:
            return
        self._run_crawler_with_progress()

    def execute_from_selected_node(self):
        """Execute the active stage starting from the selected node."""
        if not self.current_stage_graph:
            return

        selected_nodes = self.current_stage_graph.list_selected_nodes()
        if not selected_nodes:
            LOGGER.warning("No node selected for execution")
            return

        self._run_crawler_with_progress(start_node=selected_nodes[-1])

    def _run_crawler_with_progress(self, **start_kwargs) -> None:
        """Run the active stage with a dialog showing progress and a Cancel button.

        Args:
            **start_kwargs: forwarded to `StageCrawler.start`.
        """
        stage = self.current_stage_graph.stage
        crawler = stage.crawler
        dialog = ExecutionProgressDialog(crawler, parent=self)
        outcome: list[str] = []

        def on_succeeded() -> None:
            outcome.append("succeeded")

        def on_cancelled() -> None:
            outcome.append("cancelled")

        stage.execution_succeeded.connect(on_succeeded)
        stage.execution_cancelled.connect(on_cancelled)
        try:
            with dialog.watching():
                crawler.start(**start_kwargs)
        except Exception:
            NotificationManager.add_message(
                "Execution failed", fade=5, icon=":/icons/red_error"
            )
            raise
        finally:
            stage.execution_succeeded.disconnect(on_succeeded)
            stage.execution_cancelled.disconnect(on_cancelled)
            dialog.deleteLater()
        if "succeeded" in outcome:
            NotificationManager.add_message(
                "Execution succeeded", fade=5, icon=":/icons/green_check"
            )
        elif "cancelled" in outcome:
            NotificationManager.add_message("Execution cancelled", fade=5)
