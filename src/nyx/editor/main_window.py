import pathlib
import typing
import logging
import base64

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

from ..version import __version__
from .views.stage_tree_view import StageTreeView
from .views.nodes_palette_view import NodesPaletteView
from .widgets.stage_graph_editor import StageGraphEditor
from .widgets.logger_widget import LoggerWidget
from .widgets.inspector import Inspector
from .widgets.editor_toolbar import EditorToolBar
from .widgets import menubar_menus
from .widgets.stage_mdi_area import StageMdiArea
from ..utils import pyside_fn
from ..static.enums import EditorUIObject


if typing.TYPE_CHECKING:
    from nyx.api.v1 import Stage
    from ..application import NyxEditorApplication
    from ..core.layered_config import NyxConfig


LOGGER = logging.getLogger(__name__)


class NyxEditorMainWindow(QtWidgets.QMainWindow):
    _INSTANCE: NyxEditorMainWindow = None

    DEFAULT_TITLE = f"Nyx Editor v{__version__}"
    LAYOUT_VERSION = 1
    MINIMUM_SIZE = (500, 400)

    @classmethod
    def instance(cls):
        return cls._INSTANCE

    @classmethod
    def display(cls):
        if not cls._INSTANCE:
            cls._INSTANCE = cls()

        if cls._INSTANCE.isHidden():
            cls._INSTANCE.show()
        else:
            cls._INSTANCE.raise_()
            cls._INSTANCE.activateWindow()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._dock_widgets: list[QtWidgets.QDockWidget] = []
        self._is_nyx_editor_window = True
        self.setWindowTitle(self.DEFAULT_TITLE)
        self.setMinimumSize(*self.MINIMUM_SIZE)
        self.setDockNestingEnabled(True)
        self.setDockOptions(
            self.dockOptions() | QtWidgets.QMainWindow.DockOption.AllowTabbedDocks
        )

        self.undo_group = QtGui.QUndoGroup(self)

        # Initialize ui
        self.create_actions()
        self.create_widgets()
        self._create_dock_widgets()
        self.create_menubar()
        self.create_layouts()
        self.create_connections()

        self.apply_config_values()

    @property
    def config(self) -> NyxConfig:
        return self.application.config

    @property
    def current_stage_graph(self) -> StageGraphEditor | None:
        if not self.current_mdi_window:
            return None
        return self.current_mdi_window.widget()

    @property
    def current_mdi_window(self) -> QtWidgets.QMdiSubWindow | None:
        return self.mdi_area.currentSubWindow()

    @property
    def application(self):
        app: NyxEditorApplication = QtWidgets.QApplication.instance()
        return app

    @property
    def dock_widgets(self) -> list[QtWidgets.QDockWidget]:
        return self._dock_widgets

    def _create_dock(
        self,
        title: str,
        object_name: str,
        widget: QtWidgets.QWidget,
        allowed_areas: QtCore.Qt.DockWidgetArea | None = None,
    ):
        dock = QtWidgets.QDockWidget(title, self)
        dock.setObjectName(object_name)
        dock.setWidget(widget)
        if allowed_areas is not None:
            dock.setAllowedAreas(allowed_areas)
        self._dock_widgets.append(dock)
        return dock

    def create_actions(self):
        self.execute_stage_action = QtGui.QAction(
            QtGui.QIcon(":/icons/exec_stage"), "Execute stage", self
        )
        self.execute_from_selected_node_action = QtGui.QAction(
            QtGui.QIcon(":/icons/exec_from"), "Execute from selected node", self
        )
        self.execute_stage_action.triggered.connect(self.execute_stage_graph)
        self.execute_from_selected_node_action.triggered.connect(
            self.execute_from_selected_node
        )

    def create_menubar(self):
        self.menubar_file_menu = menubar_menus.FileMenu(self)
        self.menubar_edit_menu = menubar_menus.EditMenu(self)
        self.menubar_window_menu = menubar_menus.WindowMenu(self)

        self.menuBar().setNativeMenuBar(False)
        self.menuBar().addMenu(self.menubar_file_menu)
        self.menuBar().addMenu(self.menubar_edit_menu)
        self.menuBar().addMenu(self.menubar_window_menu)

    def create_widgets(self):
        self.logger_widget = LoggerWidget()
        self.stage_tree_view = StageTreeView()
        self.inspector = Inspector(self)
        self.nodes_palette_view = NodesPaletteView(self)
        self.undo_view = QtWidgets.QUndoView(self.undo_group, self)
        self.undo_view.setEmptyLabel("Stage initial state")
        self.tool_bar = EditorToolBar(self)

        # mdi area
        self.mdi_area = StageMdiArea()
        self.setCentralWidget(self.mdi_area)

    def _create_dock_widgets(self):
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
        self.logger_dock = self._create_dock(
            title="Output Log",
            object_name=EditorUIObject.LOG_OUTPUT_DOCK,
            widget=self.logger_widget,
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
        # Start from a clean slate so no stale tab groups or floating state remain
        for dock in self.dock_widgets:
            dock.setFloating(False)
            self.removeDockWidget(dock)

        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.stage_tree_dock)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.undo_dock)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.logger_dock)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.inspector_dock)
        self.addDockWidget(
            QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, self.nodes_palette_dock
        )
        self.addDockWidget(QtCore.Qt.TopDockWidgetArea, self.toolbar_dock)

        # Tabify dock widgets
        self.tabifyDockWidget(self.stage_tree_dock, self.nodes_palette_dock)
        self.tabifyDockWidget(self.stage_tree_dock, self.undo_dock)

        for dock in self.dock_widgets:
            dock.show()

        # Default in tabified group
        self.stage_tree_dock.raise_()

        # Visibility
        self.logger_dock.hide()

    def _apply_default_geometry(self):
        screen_geometry = self.screen().availableGeometry()
        default_width = int(screen_geometry.width() * 0.8)
        default_height = int(screen_geometry.height() * 0.8)
        self.resize(default_width, default_height)
        pyside_fn.move_window_to_screen_center(self)

    def create_layouts(self):
        pass

    def create_connections(self):
        self.mdi_area.subWindowActivated.connect(self.on_node_graph_window_activated)
        self.mdi_area.subWindowActivated.connect(self.update_title)
        self.undo_group.indexChanged.connect(self.update_title)
        self.undo_group.indexChanged.connect(self.inspector.update_data)

    # Events
    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        for sub_window in self.mdi_area.subWindowList():
            graph_editor: StageGraphEditor = sub_window.widget()
            result = graph_editor.maybe_save()
            if not result:
                event.ignore()
                return

        try:
            self.save_config_value()
        except Exception:
            LOGGER.exception("Failed to save config values")
        return super().closeEvent(event)

    # Config methods
    def save_config_value(self):
        self.config.values.main_window.position = (self.pos().x(), self.pos().y())
        self.config.values.main_window.size = (self.width(), self.height())
        self.config.values.main_window.layout.version = self.LAYOUT_VERSION
        self.config.values.main_window.layout.state = base64.b64encode(
            bytes(self.saveState(self.LAYOUT_VERSION))
        ).decode("ascii")
        # self.config.window_always_on_top = self.pin_window_btn.isChecked()

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
        self._load_layout_from_config()

    def _load_layout_from_config(self):
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

    def create_stage_node_graph(
        self, stage: Stage | None = None, file_path: pathlib.Path | str | None = None
    ):
        if file_path:
            stage_graph_editor_widget = StageGraphEditor.from_json_file(file_path)
        else:
            stage_graph_editor_widget = StageGraphEditor(stage)

        mdi_sub_window = self.mdi_area.addSubWindow(stage_graph_editor_widget)

        # Connect signals
        stage_graph_editor_widget.selection_model.selectionChanged.connect(
            self.inspector.update_data
        )
        return mdi_sub_window

    # Slots
    def update_title(self):
        if not self.current_stage_graph:
            self.setWindowTitle(self.DEFAULT_TITLE)
            return

        title = f"{self.DEFAULT_TITLE} - {self.current_stage_graph.windowTitle()}"
        self.setWindowTitle(title)

    @QtCore.Slot(QtWidgets.QMdiSubWindow)
    def on_node_graph_window_activated(self, mdi_window: QtWidgets.QMdiSubWindow | None):
        if mdi_window is None:
            self.stage_tree_view.set_stage(None)
            self.undo_group.setActiveStack(None)
            return

        stage_graph: StageGraphEditor = mdi_window.widget()
        self.stage_tree_view.set_stage(stage_graph.stage)
        self.undo_group.setActiveStack(stage_graph.stage.undo_stack)
        self.stage_tree_view.setSelectionModel(stage_graph.selection_model)

    def on_stage_open(self, tabbed: bool = False):
        created_new = tabbed or self.current_mdi_window is None
        sub_wnd = (
            self.create_stage_node_graph() if created_new else self.current_mdi_window
        )

        stage_graph: StageGraphEditor = sub_wnd.widget()
        file_opened = stage_graph.on_stage_open()

        if not file_opened:
            if created_new:
                self.mdi_area.removeSubWindow(sub_wnd)
            # else: cancelled opening into an existing window — leave it alone
            return

        self.mdi_area.setActiveSubWindow(sub_wnd)
        sub_wnd.show()
        self.on_node_graph_window_activated(sub_wnd)

    def on_stage_open_tabbed(self):
        self.on_stage_open(tabbed=True)

    def on_stage_new(self):
        try:
            sub_wnd = self.create_stage_node_graph()
            sub_wnd.show()
        except Exception:
            LOGGER.exception("Failed to create new stage view window")

    def on_stage_save(self):
        if self.current_stage_graph:
            self.current_stage_graph.on_stage_save()

    def on_stage_save_as(self):
        if self.current_stage_graph:
            self.current_stage_graph.on_stage_save_as()

    def execute_stage_graph(self):
        if not self.current_stage_graph:
            return
        self.current_stage_graph.stage.crawler.start()

    def execute_from_selected_node(self):
        if not self.current_stage_graph:
            return

        selected_nodes = self.current_stage_graph.list_selected_nodes()
        if not selected_nodes:
            LOGGER.warning("No node selected for execution")
            return

        self.current_stage_graph.stage.crawler.start(start_node=selected_nodes[-1])
