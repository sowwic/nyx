import typing
from uuid import UUID

from PySide6 import QtCore, QtGui, QtWidgets

if typing.TYPE_CHECKING:
    from nyx.core.node_component import NodeComponent
    from nyx.editor.graphics.graphics_node import GraphicsNode


class GraphicsPlug(QtWidgets.QGraphicsItem):
    """Row of a graphics node representing a component that can be linked.

    The plug is a child of its `GraphicsNode`. It owns its geometry and exposes
    anchors in scene coordinates so links can attach to it.
    """

    ROW_HEIGHT = 20.0
    SOCKET_RADIUS = 5.0
    SOCKET_COLOR = QtGui.QColor("#FFA637")
    SOCKET_LINKED_COLOR = QtGui.QColor("#FFD08A")
    SOCKET_OUTLINE = QtGui.QColor("#7F000000")
    LABEL_COLOR = QtGui.QColor("#CCCCCC")
    LABEL_FONT = QtGui.QFont("Zed Mono", 8)

    def __init__(self, component: NodeComponent, gr_node: GraphicsNode):
        """Initialize GraphicsPlug.

        Args:
            component (NodeComponent): component represented by the plug.
            gr_node (GraphicsNode): graphics node owning the plug.
        """
        super().__init__(gr_node)
        self._component = component
        self._uuid: UUID = component.uuid
        self._width = gr_node.width
        self._label = component.name
        self._accepts_input = False
        self._produces_output = False
        self._is_linked = False
        self.refresh()

    @property
    def component(self) -> NodeComponent:
        """NodeComponent: component represented by the plug."""
        return self._component

    @property
    def uuid(self) -> UUID:
        """UUID: uuid of the component. Stable key for the plug."""
        return self._uuid

    @property
    def gr_node(self) -> GraphicsNode:
        """GraphicsNode: node owning the plug."""
        return self.parentItem()

    @staticmethod
    def is_plug_component(component: NodeComponent) -> bool:
        """Check if the component should be shown as a plug.

        Args:
            component (NodeComponent): component to check.

        Returns:
            bool: component accepts input or produces output.
        """
        return component.accepts_input or component.produces_output

    def refresh(self):
        """Re-read the state of the component and repaint if it changed."""
        state = (
            self._component.name,
            self._component.accepts_input,
            self._component.produces_output,
            bool(self._component.links_uuids),
        )
        if state == (
            self._label,
            self._accepts_input,
            self._produces_output,
            self._is_linked,
        ):
            return
        self._label, self._accepts_input, self._produces_output, self._is_linked = state
        self.update()

    def set_width(self, width: float):
        """Set the width of the row.

        Args:
            width (float): new width, usually the width of the node.
        """
        if width == self._width:
            return
        self.prepareGeometryChange()
        self._width = width

    def input_anchor(self) -> QtCore.QPointF:
        """QtCore.QPointF: scene position input links should attach to."""
        return self.mapToScene(0.0, self.ROW_HEIGHT / 2)

    def output_anchor(self) -> QtCore.QPointF:
        """QtCore.QPointF: scene position output links should attach to."""
        return self.mapToScene(self._width, self.ROW_HEIGHT / 2)

    def boundingRect(self) -> QtCore.QRectF:
        """QtCore.QRectF: bounds of the row, including sockets sticking out."""
        r = self.SOCKET_RADIUS
        return QtCore.QRectF(-r, 0.0, self._width + 2 * r, self.ROW_HEIGHT)

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionGraphicsItem,
        widget: QtWidgets.QWidget | None = None,
    ) -> None:
        """Draw sockets and the component name.

        Args:
            painter (QtGui.QPainter): painter.
            option (QtWidgets.QStyleOptionGraphicsItem): style options.
            widget (QtWidgets.QWidget | None): painted widget.
        """
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        center_y = self.ROW_HEIGHT / 2
        r = self.SOCKET_RADIUS
        color = self.SOCKET_LINKED_COLOR if self._is_linked else self.SOCKET_COLOR
        painter.setPen(QtGui.QPen(self.SOCKET_OUTLINE, 1.0))
        painter.setBrush(color)
        if self._accepts_input:
            painter.drawEllipse(QtCore.QPointF(0.0, center_y), r, r)
        if self._produces_output:
            painter.drawEllipse(QtCore.QPointF(self._width, center_y), r, r)

        painter.setFont(self.LABEL_FONT)
        painter.setPen(self.LABEL_COLOR)
        margin = r * 2 + 2
        text_rect = QtCore.QRectF(margin, 0.0, self._width - 2 * margin, self.ROW_HEIGHT)
        align = (
            QtCore.Qt.AlignmentFlag.AlignRight
            if self._produces_output and not self._accepts_input
            else QtCore.Qt.AlignmentFlag.AlignLeft
        ) | QtCore.Qt.AlignmentFlag.AlignVCenter
        painter.drawText(text_rect, align, self._label)
