import typing
from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets

from nyx import get_main_logger
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

        self.create_actions()
        self.create_widgets()
        self.create_layouts()
        self.create_connections()

    def create_actions(self):
        pass

    def create_widgets(self):
        self.text_edit = CodeTextEdit()

    def create_layouts(self):
        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)
        self.main_layout.addWidget(self.text_edit)

    def create_connections(self):
        self.tree_view.nodes_selected.connect(self.update_text_edit)
        self.text_edit.lost_focus.connect(self.set_node_python_code)
        self.main_window.undo_group.indexChanged.connect(self.update_text_edit)

    @property
    def stage(self):
        return self.tree_view.stage

    def update_text_edit(self):
        current_node = self.tree_view.current_item()
        self.setDisabled(current_node is None)
        if not current_node:
            self.text_edit.clear()
            return
        self.text_edit.blockSignals(True)
        self.text_edit.setPlainText(current_node.get_python_code())
        self.text_edit.blockSignals(False)

    def set_node_python_code(self):
        current_node = self.tree_view.current_item()
        if not current_node:
            return
        old_code = current_node.get_python_code()
        new_code = self.text_edit.toPlainText()
        if old_code == new_code:
            return

        edit_cmd = commands.EditNodePythonCodeCommand(
            stage=self.stage, node=current_node, new_code=new_code)
        self.stage.undo_stack.push(edit_cmd)
