import typing
# from PySide2 import QtCore
# from PySide2 import QtGui
from PySide2 import QtWidgets

from nyx import get_main_logger
# from nyx.core import commands

if typing.TYPE_CHECKING:
    from nyx.editor.main_window import NyxEditorMainWindow
    from nyx.editor.views.stage_tree_view import StageTreeView

LOGGER = get_main_logger()


class AttributeEditor(QtWidgets.QWidget):
    def __init__(self, main_window: "NyxEditorMainWindow", parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self.main_window: "NyxEditorMainWindow" = main_window
        self.tree_view: "StageTreeView" = self.main_window.stage_tree_view
        self.node_field_widgets: "list[QtWidgets.QWidget]" = []

        self.create_actions()
        self.create_widgets()
        self.create_layouts()
        self.create_connections()

    def create_actions(self):
        pass

    def create_widgets(self):
        # TODO: Add scroll area
        # TODO: Add attributes table
        self.node_name_lineedit = QtWidgets.QLineEdit()
        self.node_path_lineedit = QtWidgets.QLineEdit()
        self.node_path_lineedit.setReadOnly(True)
        self.node_exec_input_line_edit = QtWidgets.QLineEdit()
        self.node_execution_start_lineedit = QtWidgets.QLineEdit()
        self.node_isactive_checkbox = QtWidgets.QCheckBox("Active")
        self.node_comment_text_edit = QtWidgets.QTextEdit("")
        self.node_position_x_spinbox = QtWidgets.QDoubleSpinBox()
        self.node_position_y_spinbox = QtWidgets.QDoubleSpinBox()

    def create_layouts(self):
        basic_properties_layout = QtWidgets.QFormLayout()
        basic_properties_layout.addRow("Name:", self.node_name_lineedit)
        basic_properties_layout.addRow("Path:", self.node_path_lineedit)
        basic_properties_layout.addRow("Exec Input:", self.node_exec_input_line_edit)
        basic_properties_layout.addRow("Child execution start", self.node_execution_start_lineedit)
        basic_properties_layout.addRow(self.node_isactive_checkbox)
        basic_properties_layout.addRow("PositionX:", self.node_position_x_spinbox)
        basic_properties_layout.addRow("PositionY:", self.node_position_y_spinbox)
        basic_properties_layout.addRow("Comment:", self.node_comment_text_edit)

        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_window.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)
        self.main_layout.addLayout(basic_properties_layout)

    def create_connections(self):
        self.tree_view.selection_changed.connect(self.update_node_data_from_treeview)

    def deactivate(self):
        pass

    def block_fields_signals(self, state: bool):
        LOGGER.debug("TODO: Add implementation of 'block_fields_signals'")

    def update_node_data_from_treeview(self):
        current_node = self.tree_view.current_item()
        if not current_node:
            self.deactivate()
            return

        self.block_fields_signals(True)
        self.node_name_lineedit.setText(current_node.name)
        self.node_path_lineedit.setText(current_node.path.as_posix())
        self.node_exec_input_line_edit.setText(
            current_node.get_input_exec_path())
        self.node_execution_start_lineedit.setText(
            current_node.get_execution_start_path(serializable=True))
        self.node_isactive_checkbox.setChecked(current_node.is_active())
        node_position = current_node.position()

        self.node_position_x_spinbox.setValue(node_position[0])
        self.node_position_y_spinbox.setValue(node_position[1])
        self.node_comment_text_edit.setText(current_node.comment())
        self.block_fields_signals(False)
