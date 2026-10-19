import typing
from uuid import UUID

from PySide6 import QtCore, QtGui, QtWidgets

from ...core import commands
from ...core.name_validator import NameValidator
from .dialogs.roles_diagnostics import RoleDiagnisticsDialog
from ..utils.common import (
    get_current_stage_graph,
    blocked_signals,
)

if typing.TYPE_CHECKING:
    from ...core.node import Node


class InspectorNodeHeader(QtWidgets.QWidget):
    """Header of the inspector showing the icon, active state and name of a node."""

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        """Initialize InspectorNodeHeader.

        Args:
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(parent=parent)
        self._node_uuid: UUID | None
        self._create_widgets()
        self._create_layouts()
        self._create_connections()

    @property
    def node(self) -> Node | None:
        """Node | None: node shown by the header."""
        if self._node_uuid is None:
            return None
        stage_graph = get_current_stage_graph()
        return stage_graph.stage.get_object(self._node_uuid)

    def _create_widgets(self) -> None:
        """Create the header widgets."""
        self.active_checkbox = QtWidgets.QCheckBox()
        self.icon_label = QtWidgets.QLabel()
        self.name_field = QtWidgets.QLineEdit()
        self.info_button = QtWidgets.QToolButton()
        self.info_button.setFixedSize(28, 28)
        self.info_button.setIcon(QtGui.QIcon(":/icons/frame_bug"))

    def _create_layouts(self) -> None:
        """Lay out the header widgets."""
        self.main_layout = QtWidgets.QHBoxLayout(self)
        self.main_layout.addWidget(self.icon_label)
        self.main_layout.addWidget(self.active_checkbox)
        self.main_layout.addWidget(self.name_field)
        self.main_layout.addWidget(self.info_button)

    def _create_connections(self) -> None:
        """Connect widget signals."""
        self.name_field.editingFinished.connect(self._on_name_edited)
        self.active_checkbox.stateChanged.connect(self._on_active_changed)
        self.info_button.clicked.connect(self._on_info_button_clicked)

    def set_node(self, node_uuid: UUID | str | None) -> None:
        """Show a node.

        Args:
            node_uuid (UUID | str | None): node uuid, None to clear the header.
        """
        self._node_uuid = node_uuid
        self._update_from_node()

    def clear(self) -> None:
        """Reset the header widgets."""
        with QtCore.QSignalBlocker(self):
            self.active_checkbox.setChecked(False)
            self.name_field.clear()

    def _update_from_node(self) -> None:
        """Refresh the widgets from the node."""
        with blocked_signals(self.active_checkbox, self.name_field):
            if self._node_uuid is None:
                self.clear()
                return

            node: Node = self.node
            # TODO: Antialiasing?
            self.icon_label.setPixmap(QtGui.QPixmap(node.get_type_icon()))
            self.active_checkbox.setEnabled(not node.is_locked)
            self.name_field.setEnabled(not node.is_locked)
            self.active_checkbox.setChecked(node.is_active())
            self.name_field.setText(node.name)

    def _on_name_edited(self):
        """Rename the node through an undoable command."""
        self.name_field.setText(
            NameValidator.get_valid_stage_object_name(self.name_field.text())
        )
        node: Node = self.node
        if self.node.name == self.name_field.text():
            return

        rename_node_command = commands.RenameNodeCommand(
            stage=node.stage, node=node, new_name=self.name_field.text()
        )
        node.stage.push_command(rename_node_command)

    def _on_active_changed(self, state: bool):
        """Set the node active state through an undoable command.

        Args:
            state (bool): new active state.
        """
        node: Node = self.node
        set_active_command = commands.SetNodeActiveStateCommand(
            stage=node.stage, node=node, state=state
        )
        node.stage.push_command(set_active_command)

    def _on_info_button_clicked(self):
        """Show the role diagnostics dialog of the node."""
        node: Node = self.node
        diagnistics_dialog = RoleDiagnisticsDialog(node.index())
        diagnistics_dialog.exec()
