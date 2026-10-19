import pathlib
import typing

from PySide6 import QtGui, QtWidgets

if typing.TYPE_CHECKING:
    from nyx.editor.widgets.stage_graph_editor import StageGraphEditor


class GraphScopeWidget(QtWidgets.QWidget):
    """Scope path field with back and root buttons for a graph editor."""

    def __init__(
        self, graph_editor: StageGraphEditor, parent: QtWidgets.QWidget = None
    ) -> None:
        """Initialize GraphScopeWidget.

        Args:
            graph_editor (StageGraphEditor): editor whose scope is shown.
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(parent)
        self.graph_editor: StageGraphEditor = graph_editor

        # Initialize ui
        self.create_actions()
        self.create_widgets()
        self.create_layouts()
        self.create_connections()

    def create_actions(self):
        """Create actions. The widget has none."""
        pass

    def create_widgets(self):
        """Create the path field and navigation buttons."""
        self.path_line_edit = QtWidgets.QLineEdit()
        self.scope_back_btn = QtWidgets.QPushButton(
            QtGui.QIcon(":/icons/arrow_back"), ""
        )
        self.scope_root_btn = QtWidgets.QPushButton(QtGui.QIcon(":/icons/home"), "")
        self.path_line_edit.setText(self.graph_editor.get_scope_path().as_posix())

    def create_layouts(self):
        """Lay out the buttons and path field."""
        self.main_layout = QtWidgets.QHBoxLayout()
        self.main_layout.setContentsMargins(5, 0, 5, 0)
        self.setLayout(self.main_layout)
        self.main_layout.addWidget(self.scope_back_btn)
        self.main_layout.addWidget(self.scope_root_btn)
        self.main_layout.addWidget(self.path_line_edit)

    def create_connections(self):
        """Connect the editor scope and the widgets."""
        self.graph_editor.scope_changed.connect(self.update_scope_text)
        self.path_line_edit.returnPressed.connect(self.set_editor_scope)
        self.scope_back_btn.clicked.connect(self.graph_editor.scope_back)
        self.scope_root_btn.clicked.connect(self.graph_editor.scope_root)

    @property
    def stage(self):
        """Stage: stage of the graph editor."""
        return self.graph_editor.stage

    def update_scope_text(self, scope_path: pathlib.PurePosixPath | str):
        """Show a scope path without triggering a scope change.

        Args:
            scope_path (pathlib.PurePosixPath | str): scope path.
        """
        self.path_line_edit.blockSignals(True)
        scope_path = str(scope_path)
        self.path_line_edit.setText(scope_path)
        self.path_line_edit.blockSignals(False)

    def set_editor_scope(self):
        """Set the editor scope to the path typed in the field."""
        self.graph_editor.set_scope_path(self.path_line_edit.text())
