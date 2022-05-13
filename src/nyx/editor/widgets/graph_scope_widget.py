import typing
import pathlib
from PySide2 import QtWidgets

if typing.TYPE_CHECKING:
    from nyx.editor.widgets.stage_graph_editor import StageGraphEditor


class GraphScopeWidget(QtWidgets.QWidget):
    def __init__(self, graph_editor: "StageGraphEditor", parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
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
        self.scope_back_btn = QtWidgets.QPushButton("<")
        self.path_line_edit.setText(self.graph_editor.get_scope_path().as_posix())

    def create_layouts(self):
        self.main_layout = QtWidgets.QHBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)
        self.main_layout.addWidget(self.scope_back_btn)
        self.main_layout.addWidget(self.path_line_edit)

    def create_connections(self):
        self.graph_editor.scope_changed.connect(self.update_scope_text)
        self.path_line_edit.returnPressed.connect(self.set_editor_scope)
        self.scope_back_btn.clicked.connect(self.graph_editor.scope_back)

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
