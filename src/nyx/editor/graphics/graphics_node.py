import typing
from collections import deque

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

from nyx.core import commands
from nyx.editor.graphics.graphics_node_title import GraphicsNodeTitle
from nyx.editor.graphics.graphics_attribute import GraphicsNodeAttribute

if typing.TYPE_CHECKING:
    from nyx.core import Node
    from nyx.editor.graphics.graphics_stage import GraphicsStage


class GraphicsNode(QtWidgets.QGraphicsItem):

    MIN_WIDTH = 100
    MIN_HEIGHT = 100
    TITLE_COLOR = QtGui.QColor("#FF313131")

    def __init__(self, node: "Node", parent=None):
        super().__init__(parent)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, enabled=True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, enabled=True)

        self.__node = None
        self.gr_attribs: "deque[GraphicsNodeAttribute]" = deque()

        self._set_node(node)
        self.setPos(self.node.position())

        self._init_sizes()
        self._init_assets()
        self._init_title()

        self.create_connections()
        self._create_gr_attributes()

    def create_connections(self):
        pass

    def _set_node(self, node: "Node | None"):
        if node:
            node.gr_node = self
            # Connect signals
        else:
            # Disconnect signals
            self.__node.gr_node = None

        self.__node = node

    def _create_gr_attributes(self):
        for _, attr in self.node.attribs.items():
            gr_attrib = GraphicsNodeAttribute(attr, self)
            self.gr_attribs.append(gr_attrib)

    def _init_sizes(self):
        self.width = self.MIN_WIDTH
        self.height = self.MIN_HEIGHT
        self.one_side_horizontal_padding = 20.0
        self.edge_roundness = 10.0
        self.edge_padding = 10.0
        self.title_horizontal_padding = 4.0
        self.title_vertical_padding = 4.0
        self.lower_padding = 8.0

    def _init_assets(self):
        # Pens, Brushes
        self._pen_default = QtGui.QPen(QtGui.QColor("#7F000000"))
        self._pen_selected = QtGui.QPen(QtGui.QColor("#FFA637"))
        self._brush_background = QtGui.QBrush(QtGui.QColor("#E3212121"))
        self._brush_title = QtGui.QBrush(self.TITLE_COLOR)

    def _init_title(self):
        self.title_item = GraphicsNodeTitle(self)

    def boundingRect(self):
        return QtCore.QRectF(0,
                             0,
                             self.width,
                             self.height).normalized()

    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionGraphicsItem, widget: QtWidgets.QWidget = None) -> None:
        # self.title_item.setVisible(self.node.scene.view.zoom > self.TEXT_ZOOM_OUT_LIMIT)

        # title
        path_title = QtGui.QPainterPath()
        path_title.setFillRule(QtCore.Qt.WindingFill)
        path_title.addRoundedRect(0, 0, self.width, self.title_height,
                                  self.edge_roundness, self.edge_roundness)
        path_title.addRect(0, self.title_height - self.edge_roundness,
                           self.edge_roundness, self.edge_roundness)
        path_title.addRect(self.width - self.edge_roundness,
                           self.title_height - self.edge_roundness, self.edge_roundness, self.edge_roundness)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(self._brush_title)
        painter.drawPath(path_title.simplified())

        # content
        path_content = QtGui.QPainterPath()
        path_content.setFillRule(QtCore.Qt.WindingFill)
        path_content.addRoundedRect(0, self.title_height, self.width,
                                    self.height - self.title_height, self.edge_roundness, self.edge_roundness)
        path_content.addRect(0, self.title_height,
                             self.edge_roundness, self.edge_roundness)
        path_content.addRect(self.width - self.edge_roundness, self.title_height,
                             self.edge_roundness, self.edge_roundness)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(self._brush_background)
        painter.drawPath(path_content.simplified())

        # outline
        # TODO: Paint prominent outline if exec input is connected
        path_outline = QtGui.QPainterPath()
        path_outline.addRoundedRect(-1, -1, self.width + 2, self.height + 2,
                                    self.edge_roundness, self.edge_roundness)
        painter.setPen(self._pen_default if not self.isSelected()
                       else self._pen_selected)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawPath(path_outline.simplified())

    @property
    def node(self):
        return self.__node

    @property
    def gr_stage(self) -> "GraphicsStage":
        return self.scene()

    @property
    def title_height(self):
        return self.title_item.height

    @property
    def title_width(self):
        return self.title_item.width

    # Events
    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        # for node in self.scene().scene.selected_nodes:
        #     node.update_connected_edges()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)

        moved_nodes = []
        new_positions = []
        for gr_node in self.gr_stage.selected_gr_nodes():
            if gr_node.pos() != gr_node.node.position():
                moved_nodes.append(gr_node.node)
                new_positions.append(gr_node.pos())

        if moved_nodes:
            move_cmd = commands.MoveNodeCommand(stage=self.node.stage,
                                                nodes=moved_nodes,
                                                new_positions=new_positions)
            self.node.stage.undo_stack.push(move_cmd)

    def mouseDoubleClickEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        return super().mouseDoubleClickEvent(event)
