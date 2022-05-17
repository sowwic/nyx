import typing

# from PySide2 import QtCore
# from PySide2 import QtGui
from PySide2 import QtWidgets

from nyx.core import commands
if typing.TYPE_CHECKING:
    from nyx.core import Node
    from nyx.editor.graphics.graphics_stage import GraphicsStage


class GraphicsNode(QtWidgets.QGraphicsItem):
    def __init__(self, node: "Node", parent=None):
        super().__init__(parent)
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

    @property
    def gr_stage(self) -> "GraphicsStage":
        return

    # Events
    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        # for node in self.scene().scene.selected_nodes:
        #     node.update_connected_edges()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)

        selected_nodes = list(self.gr_stage.selected_gr_nodes())
        new_positions = [gr_node.pos() for gr_node in selected_nodes]
        move_cmd = commands.MoveNodeCommand(stage=self.node.stage,
                                            nodes=selected_nodes,
                                            new_positions=new_positions)
        self.node.stage.undo_stack.push(move_cmd)
