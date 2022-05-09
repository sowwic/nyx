import typing
import pathlib

from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets

from nyx import get_main_logger
from nyx.editor.views.stage_graph_view import StageGraphView
from nyx.editor.views.stage_tree_view import StageTreeView
from nyx.editor.widgets import menubar_menus

if typing.TYPE_CHECKING:
    from nyx.core.config import Config


LOGGER = get_main_logger()


class NyxEditorMainWindow(QtWidgets.QMainWindow):

    __INSTANCE: "NyxEditorMainWindow" = None

    DEFAULT_TITLE = "Nyx Editor"
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
    def current_stage_graph(self) -> "StageGraphView | None":
        if not self.current_mdi_window:
            return None
        return self.current_mdi_window.widget()

    @property
    def current_mdi_window(self) -> "QtWidgets.QMdiSubWindow | None":
        return self.mdi_area.currentSubWindow()

    def create_actions(self):
        pass

    def create_menubar(self):
        self.menubar_file_menu = menubar_menus.FileMenu(self)
        self.menubar_edit_menu = menubar_menus.EditMenu(self)
        self.menubar_window_menu = menubar_menus.WindowMenu(self)

        self.menuBar().setNativeMenuBar(False)
        self.menuBar().addMenu(self.menubar_file_menu)
        self.menuBar().addMenu(self.menubar_edit_menu)
        self.menuBar().addMenu(self.menubar_window_menu)

    def create_widgets(self):
        self.stage_tree_view = StageTreeView()
        self.undo_view = QtWidgets.QUndoView(self.undo_group, self)
        self.undo_view.setEmptyLabel("Stage initial state")

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
        self.setTabPosition(QtCore.Qt.LeftDockWidgetArea, QtWidgets.QTabWidget.North)
        # Tree dock
        self.stage_tree_dock = QtWidgets.QDockWidget("Tree View")
        self.stage_tree_dock.setWidget(self.stage_tree_view)
        # Undo view
        self.undo_dock = QtWidgets.QDockWidget("Undo History")
        self.undo_dock.setWidget(self.undo_view)

        # Add dock widgets
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.stage_tree_dock)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.undo_dock)

    def create_layouts(self):
        pass

    def create_connections(self):
        self.mdi_area.subWindowActivated.connect(self.on_node_graph_window_activated)
        self.mdi_area.subWindowActivated.connect(self.update_title)
        self.undo_group.indexChanged.connect(self.update_title)

    # Events
    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
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
            graph_widget = StageGraphView.from_json_file(file_path)
        else:
            graph_widget = StageGraphView(stage)
        sub_wnd: QtWidgets.QMdiSubWindow = self.mdi_area.addSubWindow(graph_widget)
        # Signal connections
        # graph_widget.scene.signals.file_name_changed.connect(self.update_title)
        # graph_widget.scene.signals.modified.connect(self.update_title)
        # graph_widget.scene.signals.item_selected.connect(
        # self.attrib_editor.update_current_node_widget)
        # graph_widget.scene.signals.items_deselected.connect(self.attrib_editor.clear)
        # graph_widget.signals.about_to_close.connect(self.on_sub_window_close)
        # graph_widget.scene.signals.file_load_finished.connect(self.vars_widget.update_var_list)
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

        stage_graph: StageGraphView = mdi_window.widget()
        self.stage_tree_view.set_stage(stage_graph.stage)
        self.undo_group.setActiveStack(stage_graph.stage.undo_stack)

    def on_stage_open(self):
        sub_wnd = self.current_mdi_window if self.current_mdi_window else self.create_stage_node_graph()
        stage_graph: StageGraphView = sub_wnd.widget()
        stage_graph.on_stage_open()

    def on_stage_open_tabbed(self):
        sub_wnd = self.create_stage_node_graph()
        stage_graph: StageGraphView = sub_wnd.widget()
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
