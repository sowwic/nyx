import typing
import pathlib

from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets

from nyx._version import _version
from nyx import get_main_logger
from nyx.editor.views.stage_tree_view import StageTreeView
from nyx.editor.widgets.stage_graph_editor import StageGraphEditor
from nyx.editor.widgets.logger_widget import LoggerWidget
from nyx.editor.widgets.attribute_editor import AttributeEditor
from nyx.editor.widgets.code_editor import CodeEditor
from nyx.editor.widgets.editor_toolbar import EditorToolBar
from nyx.editor.widgets import menubar_menus
from nyx.utils import pyside_fn

if typing.TYPE_CHECKING:
    from nyx.core.config import Config


LOGGER = get_main_logger()


class NyxEditorMainWindow(QtWidgets.QMainWindow):

    __INSTANCE: "NyxEditorMainWindow" = None

    DEFAULT_TITLE = f"Nyx Editor v{_version}"
    MINIMUM_SIZE = (500, 400)

    @classmethod
    def instance(cls):
        return cls.__INSTANCE

    @classmethod
    def display(cls):
        if not cls.__INSTANCE:
            cls.__INSTANCE = cls()

        if cls.__INSTANCE.isHidden():
            cls.__INSTANCE.show()
        else:
            cls.__INSTANCE.raise_()
            cls.__INSTANCE.activateWindow()

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.DEFAULT_TITLE)
        self.setMinimumSize(*self.MINIMUM_SIZE)
        self.undo_group = QtWidgets.QUndoGroup(self)

        # Initialize ui
        self.create_actions()
        self.create_widgets()
        self.create_menubar()
        self.create_layouts()
        self.create_connections()

        self.apply_config_values()

    @property
    def config(self) -> "Config":
        return QtWidgets.QApplication.instance().config()

    @property
    def current_stage_graph(self) -> "StageGraphEditor | None":
        if not self.current_mdi_window:
            return None
        return self.current_mdi_window.widget()

    @property
    def current_mdi_window(self) -> "QtWidgets.QMdiSubWindow | None":
        return self.mdi_area.currentSubWindow()

    def create_actions(self):
        self.execute_stage_action = QtWidgets.QAction(
            pyside_fn.get_standard_icon(self, "SP_MediaPlay"), "Execute stage", self)
        self.execute_from_selected_node_action = QtWidgets.QAction(
            pyside_fn.get_standard_icon(self, "SP_MediaSkipForward"), "Execute from selected node", self)
        self.execute_stage_action.triggered.connect(self.execute_stage_graph)
        self.execute_from_selected_node_action.triggered.connect(self.execute_from_selected_node)

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
        self.code_editor = CodeEditor(self)
        self.attrib_editor = AttributeEditor(self)
        self.undo_view = QtWidgets.QUndoView(self.undo_group, self)
        self.undo_view.setEmptyLabel("Stage initial state")
        self.tool_bar = EditorToolBar(self)

        # mdi area
        self.mdi_area = QtWidgets.QMdiArea()
        self.setCentralWidget(self.mdi_area)
        self.mdi_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.mdi_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.mdi_area.setViewMode(QtWidgets.QMdiArea.TabbedView)
        self.mdi_area.setDocumentMode(True)
        self.mdi_area.setTabsClosable(True)
        self.mdi_area.setTabsMovable(True)

        # Dock Widgets
        self.setTabPosition(QtCore.Qt.RightDockWidgetArea, QtWidgets.QTabWidget.East)
        self.setTabPosition(QtCore.Qt.LeftDockWidgetArea, QtWidgets.QTabWidget.West)
        self.setTabPosition(QtCore.Qt.BottomDockWidgetArea, QtWidgets.QTabWidget.North)
        # Tree dock
        self.stage_tree_dock = QtWidgets.QDockWidget("Tree View")
        self.stage_tree_dock.setWidget(self.stage_tree_view)
        # Undo view dock
        self.undo_dock = QtWidgets.QDockWidget("Undo History")
        self.undo_dock.setWidget(self.undo_view)
        # Logger dock
        self.logger_dock = QtWidgets.QDockWidget("Output Log")
        self.logger_dock.setWidget(self.logger_widget)
        # Code editor dock
        self.code_editor_dock = QtWidgets.QDockWidget("Code Editor")
        self.code_editor_dock.setWidget(self.code_editor)
        # Toolbar dock
        self.toolbar_dock = QtWidgets.QDockWidget("Tools")
        self.toolbar_dock.setAllowedAreas(
            QtCore.Qt.TopDockWidgetArea | QtCore.Qt.BottomDockWidgetArea)
        self.toolbar_dock.setWidget(self.tool_bar)
        # Attribute editor dock
        self.attrib_editor_dock = QtWidgets.QDockWidget("Attribute Editor")
        self.attrib_editor_dock.setWidget(self.attrib_editor)

        # Add dock widgets
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.stage_tree_dock)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.undo_dock)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.logger_dock)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.attrib_editor_dock)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.code_editor_dock)
        self.addDockWidget(QtCore.Qt.TopDockWidgetArea, self.toolbar_dock)

    def create_layouts(self):
        pass

    def create_connections(self):
        self.mdi_area.subWindowActivated.connect(self.on_node_graph_window_activated)
        self.mdi_area.subWindowActivated.connect(self.update_title)
        self.undo_group.indexChanged.connect(self.update_title)

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
        self.config.window_position = (self.pos().x(), self.pos().y())
        self.config.window_size = (self.width(), self.height())
        # self.config.window_always_on_top = self.pin_window_btn.isChecked()

    def apply_config_values(self):
        """Apply values from application config."""
        self.resize(QtCore.QSize(*self.config.window_size))
        if not self.config.window_position:
            center_position: QtCore.QPoint = self.pos(
            ) + QtWidgets.QApplication.primaryScreen().geometry().center() - self.geometry().center()
            self.config.window_position = (center_position.x(), center_position.y())
        self.move(QtCore.QPoint(*self.config.window_position))

        # TODO: add always on top toggle
        # self.toggle_always_on_top(self.config.window_always_on_top)
        LOGGER.setLevel(self.config.logging_level)

    def reset_application_config(self):
        """Reset application config and apply changes."""
        QtWidgets.QApplication.instance().reset_config()
        self.apply_config_values()

    def create_stage_node_graph(self, stage=None, file_path: "pathlib.Path | str" = None):
        if file_path:
            graph_widget = StageGraphEditor.from_json_file(file_path)
        else:
            graph_widget = StageGraphEditor(stage)
        sub_wnd: QtWidgets.QMdiSubWindow = self.mdi_area.addSubWindow(graph_widget)
        return sub_wnd

    # Slots
    def update_title(self):
        if not self.current_stage_graph:
            self.setWindowTitle(self.DEFAULT_TITLE)
            return

        title = f"{self.DEFAULT_TITLE} - {self.current_stage_graph.windowTitle()}"
        self.setWindowTitle(title)

    @QtCore.Slot(QtWidgets.QMdiSubWindow)
    def on_node_graph_window_activated(self, mdi_window: QtWidgets.QMdiSubWindow):
        if mdi_window is None:
            self.stage_tree_view.set_stage(None)
            self.undo_group.setActiveStack(None)
            return

        stage_graph: StageGraphEditor = mdi_window.widget()
        self.stage_tree_view.set_stage(stage_graph.stage)
        self.undo_group.setActiveStack(stage_graph.stage.undo_stack)

    def on_stage_open(self):
        sub_wnd = self.current_mdi_window if self.current_mdi_window else self.create_stage_node_graph()
        stage_graph: StageGraphEditor = sub_wnd.widget()
        stage_graph.on_stage_open()

    def on_stage_open_tabbed(self):
        sub_wnd = self.create_stage_node_graph()
        stage_graph: StageGraphEditor = sub_wnd.widget()
        file_opened: bool = stage_graph.on_stage_open()
        if not file_opened:
            self.mdi_area.removeSubWindow(sub_wnd)

    def on_stage_new(self):
        try:
            sub_wnd = self.create_stage_node_graph()
            sub_wnd.show()
        except Exception:
            LOGGER.exception('Failed to create new stage view window')

    def on_stage_save(self):
        if self.current_stage_graph:
            self.current_stage_graph.on_stage_save()

    def on_stage_save_as(self):
        if self.current_stage_graph:
            self.current_stage_graph.on_stage_save_as()

    def execute_stage_graph(self):
        if not self.current_stage_graph:
            return
        self.current_stage_graph.stage.executor.run()

    def execute_from_selected_node(self):
        if not self.current_stage_graph:
            return

        selected_gr_node = self.current_stage_graph.gr_stage.get_last_selected_gr_node()
        if not selected_gr_node:
            LOGGER.warning("No node selected for execution")
            return

        self.current_stage_graph.stage.executor.run(selected_gr_node.node)
