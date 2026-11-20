from __future__ import annotations

import pathlib
import typing

from PySide6 import QtGui, QtWidgets

if typing.TYPE_CHECKING:
    from nyx.editor.widgets.stage_graph_editor import StageGraphEditor


class GraphScopeWidget(QtWidgets.QWidget):
    """Scope path field with back and root buttons, following one editor at a time."""

    MINIMUM_PATH_WIDTH = 240

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        """Initialize GraphScopeWidget.

        Args:
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(parent)
        self.graph_editor: StageGraphEditor | None = None

        # Initialize ui
        self.create_actions()
        self.create_widgets()
        self.create_layouts()
        self.create_connections()
        self.set_graph_editor(None)

    def create_actions(self):
        """Create actions. The widget has none."""
        pass

    def create_widgets(self):
        """Create the path field and navigation buttons."""
        self.path_line_edit = QtWidgets.QLineEdit()
        self.path_line_edit.setMinimumWidth(self.MINIMUM_PATH_WIDTH)
        self.scope_back_btn = QtWidgets.QToolButton()
        self.scope_back_btn.setIcon(QtGui.QIcon(":/icons/arrow_back"))
        self.scope_back_btn.setToolTip("Scope up")
        self.scope_root_btn = QtWidgets.QToolButton()
        self.scope_root_btn.setIcon(QtGui.QIcon(":/icons/home"))
        self.scope_root_btn.setToolTip("Scope root")

    def create_layouts(self):
        """Lay out the buttons and path field."""
        self.main_layout = QtWidgets.QHBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(6)
        self.setLayout(self.main_layout)
        self.main_layout.addWidget(self.scope_back_btn)
        self.main_layout.addWidget(self.scope_root_btn)
        self.main_layout.addWidget(self.path_line_edit)

    def create_connections(self):
        """Connect the widgets. The editor is connected by `set_graph_editor`."""
        self.path_line_edit.returnPressed.connect(self.set_editor_scope)
        self.scope_back_btn.clicked.connect(self._scope_back)
        self.scope_root_btn.clicked.connect(self._scope_root)

    def set_graph_editor(self, graph_editor: StageGraphEditor | None) -> None:
        """Follow the scope of an editor.

        Args:
            graph_editor (StageGraphEditor | None): editor to follow, None when no
                editor is open.
        """
        if self.graph_editor is not None:
            self.graph_editor.scope_changed.disconnect(self.update_scope_text)
        self.graph_editor = graph_editor
        self.setEnabled(graph_editor is not None)
        if graph_editor is None:
            self.update_scope_text("")
            return
        graph_editor.scope_changed.connect(self.update_scope_text)
        self.update_scope_text(graph_editor.get_scope_path())

    @property
    def stage(self):
        """Stage | None: stage of the followed editor."""
        return self.graph_editor.stage if self.graph_editor else None

    def update_scope_text(self, scope_path: pathlib.PurePosixPath | str):
        """Show a scope path without triggering a scope change.

        Args:
            scope_path (pathlib.PurePosixPath | str): scope path.
        """
        self.path_line_edit.blockSignals(True)
        scope_path = scope_path.as_posix() if scope_path != "" else ""
        self.path_line_edit.setText(scope_path)
        self.path_line_edit.blockSignals(False)

    def set_editor_scope(self):
        """Set the editor scope to the path typed in the field."""
        if self.graph_editor is not None:
            self.graph_editor.set_scope_path(self.path_line_edit.text())

    def _scope_back(self) -> None:
        """Move the followed editor to the parent scope."""
        if self.graph_editor is not None:
            self.graph_editor.scope_back()

    def _scope_root(self) -> None:
        """Move the followed editor to the root scope."""
        if self.graph_editor is not None:
            self.graph_editor.scope_root()
