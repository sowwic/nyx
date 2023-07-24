import typing
import pathlib
from PySide2 import QtCore
# from PySide2 import QtGui
from PySide2 import QtWidgets

from nyx import get_main_logger
from nyx.core import Node
from nyx.core import commands
from nyx.editor.widgets.attributes_table import AttributesTable
from nyx.editor.widgets.text_edit_widget import NyxTextEdit

if typing.TYPE_CHECKING:
    from nyx.editor.main_window import NyxEditorMainWindow

LOGGER = get_main_logger()


class AttributeEditor(QtWidgets.QWidget):
    def __init__(self, main_window: "NyxEditorMainWindow", parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self.__node: Node = None
        self.main_window: "NyxEditorMainWindow" = main_window

        self.create_actions()
        self.create_widgets()
        self.create_layouts()
        self.create_connections()

    def create_actions(self):
        pass

    def create_widgets(self):
        # TODO: Add scroll area
        self.node_name_lineedit = QtWidgets.QLineEdit()
        self.node_path_lineedit = QtWidgets.QLineEdit()
        self.node_path_lineedit.setReadOnly(True)
        self.node_exec_input_line_edit = QtWidgets.QLineEdit()
        self.node_execution_start_lineedit = QtWidgets.QLineEdit()
        self.node_isactive_checkbox = QtWidgets.QCheckBox("Active")
        self.node_comment_text_edit = NyxTextEdit()
        self.node_position_x_spinbox = QtWidgets.QDoubleSpinBox()
        self.node_position_y_spinbox = QtWidgets.QDoubleSpinBox()
        self.node_position_x_spinbox.setButtonSymbols(
            QtWidgets.QAbstractSpinBox.NoButtons)
        self.node_position_y_spinbox.setButtonSymbols(
            QtWidgets.QAbstractSpinBox.NoButtons)
        self.node_position_x_spinbox.setRange(-64000, 64000)
        self.node_position_y_spinbox.setRange(-64000, 64000)

        self.attributes_table = AttributesTable(self)

    def create_layouts(self):
        position_layout = QtWidgets.QHBoxLayout()
        position_layout.addWidget(QtWidgets.QLabel("X:"))
        position_layout.addWidget(self.node_position_x_spinbox)
        position_layout.addWidget(QtWidgets.QLabel("Y:"))
        position_layout.addWidget(self.node_position_y_spinbox)
        position_layout.addStretch()

        basic_properties_layout = QtWidgets.QFormLayout()
        basic_properties_layout.addRow(self.node_isactive_checkbox)
        basic_properties_layout.addRow("Name:", self.node_name_lineedit)
        basic_properties_layout.addRow("Path:", self.node_path_lineedit)
        basic_properties_layout.addRow(
            "Exec Input:", self.node_exec_input_line_edit)
        basic_properties_layout.addRow(
            "Execution start:", self.node_execution_start_lineedit)
        basic_properties_layout.addRow("Position:", position_layout)
        basic_properties_layout.addRow("Comment:", self.node_comment_text_edit)

        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_window.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)
        self.main_layout.addLayout(basic_properties_layout)
        self.main_layout.addWidget(self.attributes_table)

    def create_connections(self):
        self.tree_view.selection_changed.connect(
            self.update_node_data_from_treeview)
        self.main_window.undo_group.indexChanged.connect(
            self.update_node_data_from_treeview)
        self.node_name_lineedit.editingFinished.connect(self.apply_name_edit)
        self.node_exec_input_line_edit.editingFinished.connect(
            self.apply_exec_input_edit)
        self.node_execution_start_lineedit.editingFinished.connect(
            self.apply_execution_start_edit)
        self.node_isactive_checkbox.toggled.connect(self.apply_active_toggle)
        self.node_comment_text_edit.editingFinished.connect(
            self.apply_comment_edit)
        self.node_position_x_spinbox.editingFinished .connect(
            self.apply_position_edit)
        self.node_position_y_spinbox.editingFinished .connect(
            self.apply_position_edit)

    @property
    def tree_view(self):
        return self.main_window.stage_tree_view

    @property
    def current_stage_graph(self):
        return self.main_window.current_stage_graph

    @property
    def code_editor(self):
        return self.main_window.code_editor

    @property
    def node(self):
        return self.__node

    @node.setter
    def node(self, node: Node):
        self.__node = node
        if self.__node is None:
            self.set_fields_enabled(False)
            return

        self.block_fields_signals(True)
        self.set_fields_enabled(True)
        self.set_data_from_node(self.node)
        self.attributes_table.update_node_data()
        self.code_editor.current_node = node
        self.block_fields_signals(False)

    def set_fields_enabled(self, state: bool):
        for field in [self.node_name_lineedit,
                      self.node_path_lineedit,
                      self.node_exec_input_line_edit,
                      self.node_execution_start_lineedit,
                      self.node_comment_text_edit]:
            if not state:
                field.clear()
            field.setEnabled(state)
        self.code_editor.setEnabled(state)

        if not state:
            self.node_isactive_checkbox.setChecked(False)
            self.attributes_table.setRowCount(0)
        self.node_isactive_checkbox.setEnabled(state)

        for spinbox in [self.node_position_x_spinbox,
                        self.node_position_y_spinbox]:
            if not state:
                spinbox.setValue(0.0)
            spinbox.setEnabled(state)

    def block_fields_signals(self, state: bool):
        for widget in [self.node_name_lineedit,
                       self.node_path_lineedit,
                       self.node_exec_input_line_edit,
                       self.node_execution_start_lineedit,
                       self.node_isactive_checkbox,
                       self.node_comment_text_edit,
                       self.node_position_x_spinbox,
                       self.node_position_y_spinbox]:
            widget.blockSignals(state)

    def update_node_data_from_stage_graph(self, selected_paths):
        current_stage_node = self.current_stage_graph.stage.node(
            selected_paths[-1])
        self.node = None or current_stage_node

    def update_node_data_from_treeview(self):
        self.node = self.tree_view.current_node()

    def set_data_from_node(self, node):
        self.node_name_lineedit.setText(node.name)
        self.node_path_lineedit.setText(node.path.as_posix())
        self.node_exec_input_line_edit.setText(
            node.get_input_exec_path(serializable=True))
        self.node_execution_start_lineedit.setText(
            node.get_execution_start_path(serializable=True))
        self.node_isactive_checkbox.setChecked(node.is_active())
        node_position = node.position()
        if not isinstance(node_position, QtCore.QPointF):
            node_position = QtCore.QPointF(*node_position)

        self.node_position_x_spinbox.setValue(node_position.x())
        self.node_position_y_spinbox.setValue(node_position.y())
        self.node_comment_text_edit.setText(node.comment())

    def apply_name_edit(self):
        current_node = self.tree_view.current_node()
        if not current_node:
            return

        new_name = self.node_name_lineedit.text()
        if new_name == current_node.name:
            return

        rename_cmd = commands.RenameNodeCommand(stage=current_node.stage,
                                                node=current_node,
                                                new_name=new_name)
        current_node.stage.undo_stack.push(rename_cmd)

    def apply_exec_input_edit(self):
        current_node = self.tree_view.current_node()
        if not current_node:
            return

        new_path = pathlib.PurePosixPath(self.node_exec_input_line_edit.text())
        if new_path == pathlib.PurePosixPath("."):
            new_path = None

        if new_path == current_node.get_input_exec_path():
            return

        source_node = current_node.stage.node(new_path)
        if source_node is None:
            set_exec_input_cmd = commands.DisconnectNodeInputExecCommand(stage=current_node.stage,
                                                                         node=current_node)
        else:
            if current_node.is_input_exec_cyclic(source_node) or current_node is source_node:
                LOGGER.warning(
                    f"Cyclic exec path: {source_node.path} <-> {current_node.path}")
                self.update_node_data_from_treeview()
                return
            set_exec_input_cmd = commands.ConnectNodeExecCommand(stage=current_node.stage,
                                                                 output_node=source_node,
                                                                 input_node=current_node)
        current_node.stage.undo_stack.push(set_exec_input_cmd)

    def apply_execution_start_edit(self):
        current_node = self.tree_view.current_node()
        if not current_node:
            return

        new_path = pathlib.PurePosixPath(
            self.node_execution_start_lineedit.text())
        if new_path == pathlib.PurePosixPath("."):
            new_path = None

        if new_path == current_node.get_execution_start_path():
            return

        # if new_path and current_node.path not in new_path.parents:
        if new_path and not current_node.is_parent_of(new_path):
            LOGGER.warning(
                f"Node({new_path}) is not a child of {current_node}")
            self.update_node_data_from_treeview()
            return

        set_execution_start_cmd = commands.SetNodeExecStartCommand(stage=current_node.stage,
                                                                   node=current_node,
                                                                   path=new_path)
        current_node.stage.undo_stack.push(set_execution_start_cmd)

    def apply_active_toggle(self):
        current_node = self.tree_view.current_node()
        if not current_node:
            return
        new_state = self.node_isactive_checkbox.isChecked()

        set_active_cmd = commands.SetNodeActiveStateCommand(stage=current_node.stage,
                                                            node=current_node,
                                                            state=new_state)
        current_node.stage.undo_stack.push(set_active_cmd)

    def apply_comment_edit(self):
        current_node = self.tree_view.current_node()
        if not current_node:
            return

        new_comment = self.node_comment_text_edit.toPlainText()
        if new_comment == current_node.comment():
            return

        set_comment_cmd = commands.SetNodeCommentCommand(stage=current_node.stage,
                                                         node=current_node,
                                                         comment=new_comment)
        current_node.stage.undo_stack.push(set_comment_cmd)

    def apply_position_edit(self):
        current_node = self.tree_view.current_node()
        if not current_node:
            return

        new_position = QtCore.QPointF(self.node_position_x_spinbox.value(),
                                      self.node_position_y_spinbox.value())
        if new_position == current_node.position():
            return

        move_cmd = commands.MoveNodeCommand(stage=current_node.stage,
                                            nodes=[current_node],
                                            new_positions=[new_position])
        current_node.stage.undo_stack.push(move_cmd)
