import typing
import pathlib
from PySide2 import QtGui
from PySide2 import QtWidgets

if typing.TYPE_CHECKING:
    from nyx.editor.main_window import NyxEditorMainWindow
    from nyx.editor.widgets.stage_graph_editor import StageGraphEditor


class GraphScopeWidget(QtWidgets.QWidget):
    def __init__(self, graph_editor: "StageGraphEditor", parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self.__icon_scope_back: QtGui.QIcon = None
        self.__icon_scope_root: QtGui.QIcon = None
        self.graph_editor: "StageGraphEditor" = graph_editor

        # Initialize ui
        self.create_actions()
        self.create_widgets()
        self.create_layouts()
        self.create_connections()

    def create_actions(self):
        pass

    def create_widgets(self):
        self.path_line_edit = QtWidgets.QLineEdit()
        self.scope_back_btn = QtWidgets.QPushButton(self.icon_scope_back, "")
        self.scope_root_btn = QtWidgets.QPushButton(self.icon_scope_root, "")
        self.path_line_edit.setText(self.graph_editor.get_scope_path().as_posix())

    def create_layouts(self):
        self.main_layout = QtWidgets.QHBoxLayout()
        self.main_layout.setContentsMargins(5, 0, 5, 0)
        self.setLayout(self.main_layout)
        self.main_layout.addWidget(self.scope_back_btn)
        self.main_layout.addWidget(self.scope_root_btn)
        self.main_layout.addWidget(self.path_line_edit)

    def create_connections(self):
        self.graph_editor.scope_changed.connect(self.update_scope_text)
        self.path_line_edit.returnPressed.connect(self.set_editor_scope)
        self.scope_back_btn.clicked.connect(self.graph_editor.scope_back)
        self.scope_root_btn.clicked.connect(self.graph_editor.scope_root)

    @property
    def icon_scope_back(self):
        if self.__icon_scope_back:
            return self.__icon_scope_back
        main_window: "NyxEditorMainWindow" = QtWidgets.QApplication.instance().main_window()
        pixmap = QtWidgets.QStyle.SP_FileDialogBack
        self.__icon_scope_back = main_window.style().standardIcon(pixmap)
        return self.__icon_scope_back

    @property
    def icon_scope_root(self):
        if self.__icon_scope_root:
            return self.__icon_scope_root
        main_window: "NyxEditorMainWindow" = QtWidgets.QApplication.instance().main_window()
        pixmap = QtWidgets.QStyle.SP_DirHomeIcon
        self.__icon_scope_root = main_window.style().standardIcon(pixmap)
        return self.__icon_scope_root

    @property
    def stage(self):
        return self.graph_editor.stage

    def update_scope_text(self, scope_path: "pathlib.PurePosixPath | str"):
        self.path_line_edit.blockSignals(True)
        scope_path = str(scope_path)
        self.path_line_edit.setText(scope_path)
        self.path_line_edit.blockSignals(False)

    def set_editor_scope(self):
        self.graph_editor.set_scope_path(self.path_line_edit.text())
