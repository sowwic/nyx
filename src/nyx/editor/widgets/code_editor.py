import typing
from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets

from nyx import get_main_logger
from nyx.core import Node
from nyx.core import commands

if typing.TYPE_CHECKING:
    from nyx.editor.main_window import NyxEditorMainWindow
    from nyx.editor.views.stage_tree_view import StageTreeView

LOGGER = get_main_logger()


class CodeTextEdit(QtWidgets.QPlainTextEdit):

    lost_focus = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__("", parent)

    def focusOutEvent(self, event: QtGui.QFocusEvent) -> None:
        self.lost_focus.emit()
        return super().focusOutEvent(event)


class CodeEditor(QtWidgets.QWidget):

    def __init__(self, main_window: "NyxEditorMainWindow", parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self.main_window: "NyxEditorMainWindow" = main_window
        self.tree_view: "StageTreeView" = self.main_window.stage_tree_view
        self.__current_node: Node = None

        self.create_actions()
        self.create_widgets()
        self.create_layouts()
        self.create_connections()

    def create_actions(self):
        pass

    def create_widgets(self):
        self.text_edit = CodeTextEdit()
        self.run_code_button = QtWidgets.QPushButton("Run")

    def create_layouts(self):
        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)
        self.main_layout.addWidget(self.text_edit)
        self.main_layout.addWidget(self.run_code_button)

    def create_connections(self):
        self.text_edit.lost_focus.connect(self.save_current_node_python_code)
        self.run_code_button.clicked.connect(
            lambda: self.current_node.execute_code())

    @property
    def stage(self):
        return self.tree_view.stage

    @property
    def current_node(self):
        return self.__current_node

    @current_node.setter
    def current_node(self, node: Node):
        self.__current_node = node
        self.update_text_edit()

    def update_text_edit(self):
        self.text_edit.blockSignals(True)
        self.setEnabled(self.current_node is not None)
        if self.current_node:
            self.text_edit.setPlainText(self.current_node.get_python_code())
        else:
            self.text_edit.clear()
        self.text_edit.blockSignals(False)

    def save_current_node_python_code(self):
        if not self.current_node:
            return
        old_code = self.current_node.get_python_code()
        new_code = self.text_edit.toPlainText()
        if old_code == new_code:
            return

        edit_cmd = commands.EditNodePythonCodeCommand(
            stage=self.stage, node=self.current_node, new_code=new_code)
        self.stage.undo_stack.push(edit_cmd)
