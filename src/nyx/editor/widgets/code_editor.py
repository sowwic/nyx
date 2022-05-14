import typing
from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets

from nyx import get_main_logger

if typing.TYPE_CHECKING:
    from nyx.core import Node
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

    def __init__(self, tree_view: "StageTreeView", parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self.tree_view: StageTreeView = tree_view

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
        self.text_edit.textChanged.connect(self.set_node_python_code)

    def update_text_edit(self, selected_nodes: "list[Node]"):
        self.setEnabled(len(selected_nodes))
        if not selected_nodes:
            self.text_edit.clear()
            return
        node = selected_nodes[-1]
        self.text_edit.blockSignals(True)
        self.text_edit.setPlainText(node.get_python_code())
        self.text_edit.blockSignals(False)

    def set_node_python_code(self):
        current_node = self.tree_view.current_item()
        if current_node:
            current_node.set_python_code(self.text_edit.toPlainText())
