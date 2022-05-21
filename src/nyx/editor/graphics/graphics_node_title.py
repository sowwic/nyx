from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets


class GraphicsNodeTitle(QtWidgets.QGraphicsTextItem):

    def __init__(self, gr_node, text='', is_editable=False):
        super().__init__(text, gr_node)
        self.gr_node = gr_node
        self.is_editable = is_editable

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
        new_text = new_text.strip()
        if new_text == self.gr_node.title:
            return
        # self.gr_node.node.signals.title_edited.emit(new_text)
