import typing

from PySide6 import QtCore, QtGui, QtWidgets

from nyx.core import commands
from nyx.core.name_validator import NameValidator

if typing.TYPE_CHECKING:
    from nyx.editor.graphics.graphics_node import GraphicsNode


class GraphicsNodeTitle(QtWidgets.QGraphicsTextItem):
    TITLE_FONT = QtGui.QFont("Zed Mono", 10)

    def __init__(self, gr_node: GraphicsNode):
        self.gr_node = gr_node
        super().__init__(self.gr_node.node.name, gr_node)
        self.setFont(self.TITLE_FONT)
        self.font().setBold(True)

    @property
    def height(self):
        return self.boundingRect().height()

    @property
    def width(self):
        return self.boundingRect().width()

    def edit(self):
        line_edit = QtWidgets.QLineEdit()
        line_edit_proxy = QtWidgets.QGraphicsProxyWidget(self)
        line_edit_proxy.setWidget(line_edit)
        line_edit.editingFinished.connect(lambda: self.apply_edit(line_edit.text()))
        line_edit.editingFinished.connect(line_edit_proxy.deleteLater)
        line_edit.setFont(self.font())

        line_edit.setMaximumWidth(self.gr_node.width)
        line_edit.setText(self.toPlainText())
        line_edit.setFocus(QtCore.Qt.MouseFocusReason)

    def apply_edit(self, new_text):
        new_text = NameValidator.get_valid_stage_object_name(new_text)
        if not new_text or new_text == self.gr_node.node.name:
            return
        rename_cmd = commands.RenameNodeCommand(
            stage=self.gr_node.node.stage, node=self.gr_node.node, new_name=new_text
        )
        self.gr_node.node.stage.push_command(rename_cmd)
