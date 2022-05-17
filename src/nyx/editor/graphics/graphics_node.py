import typing

# from PySide2 import QtCore
# from PySide2 import QtGui
from PySide2 import QtWidgets

if typing.TYPE_CHECKING:
    from nyx.core import Node


class GraphicsNode(QtWidgets.QGraphicsItem):
    def __init__(self, node: "Node", parent=None):
        super(GraphicsNode, self).__init__(parent)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable)

        self.__node = node
        # self.node.gr_node = self
        self.create_connections()

    def create_connections(self):
        pass

    @property
    def node(self):
        return self.__node
