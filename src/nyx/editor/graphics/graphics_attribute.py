import typing

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

if typing.TYPE_CHECKING:
    from nyx.core.attribute import Attribute
    from nyx.editor.graphics.graphics_node import GraphicsNode


class GraphicsNodeAttribute(QtWidgets.QGraphicsItem):

    HEIGHT = 30.0

    def __init__(self, attr: "Attribute", gr_node: "GraphicsNode" = None) -> None:
        super().__init__(gr_node)
        self.__attr = attr
        self.__gr_node = gr_node
        self.__index = len(gr_node.gr_attribs)

    @property
    def attr(self) -> "Attribute":
        return self.__attr

    @property
    def gr_node(self) -> "GraphicsNode":
        return self.__gr_node

    @property
    def index(self) -> int:
        return self.__index

    def boundingRect(self) -> QtCore.QRectF:
        return QtCore.QRectF(0,
                             0,
                             self.gr_node.width,
                             self.HEIGHT).normalized()

    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionGraphicsItem, widget: QtWidgets.QWidget = None) -> None:
        pass
