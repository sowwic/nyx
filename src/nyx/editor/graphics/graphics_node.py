import typing
from uuid import UUID

from PySide6 import QtCore, QtGui, QtWidgets

from .graphics_node_title import GraphicsNodeTitle
from .graphics_plug import GraphicsPlug
from ..utils.common import build_role_tooltip_html, are_hover_diagnostics_enabled
from ...core import commands

if typing.TYPE_CHECKING:
    from nyx.core import Node
    from nyx.editor.graphics.graphics_stage import GraphicsStage


class GraphicsNode(QtWidgets.QGraphicsItem):
    """Graphics item representing a node in the stage scene.

    The item is a view of its node: `refresh` re-reads everything from the node
    and `update_layout` recomputes the geometry. Geometry is only changed there.
    """

    MIN_WIDTH = 100
    MIN_HEIGHT = 100
    TITLE_COLOR = QtGui.QColor("#FF313131")
    BACKGROUND_COLOR = QtGui.QColor("#E3212121")
    REFERENCE_NODE_BACKGROUND = QtGui.QColor("#2182CF")
    ICON_RECT = QtCore.QRect(8, 6, 16, 16)
    TITLE_OFFSET_X = 28.0

    def __init__(self, node: Node, parent=None):
        """Initialize GraphicsNode.

        Args:
            node (Node): node to show.
            parent (QtWidgets.QGraphicsItem | None): parent item.
        """
        super().__init__(parent)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, enabled=True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, enabled=True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, enabled=True)
        self.setAcceptHoverEvents(True)

        self._node = node
        self._plugs: dict[UUID, GraphicsPlug] = {}
        self._icon = QtGui.QIcon()
        self._path_title = QtGui.QPainterPath()
        self._path_content = QtGui.QPainterPath()
        self._path_outline = QtGui.QPainterPath()

        self._init_sizes()
        self._init_assets()
        self.title_item = GraphicsNodeTitle(self)
        self.title_item.setPos(self.TITLE_OFFSET_X, 0)

        self.refresh()

    def _init_sizes(self):
        """Initialize size and padding values."""
        self.width = self.MIN_WIDTH
        self.height = self.MIN_HEIGHT
        self.edge_roundness = 10.0
        self.title_horizontal_padding = 4.0
        self.plugs_top_padding = 4.0
        self.lower_padding = 8.0

    def _init_assets(self):
        """Create the pens and brushes."""
        self._pen_default = QtGui.QPen(QtGui.QColor("#7F000000"))
        self._pen_selected = QtGui.QPen(QtGui.QColor("#FFA637"))
        self._brush_title = QtGui.QBrush(self.TITLE_COLOR)
        self._brush_background = QtGui.QBrush(self.BACKGROUND_COLOR)

    # ======== Properties ========= #

    @property
    def node(self) -> Node:
        """Node: node shown by the item."""
        return self._node

    @property
    def gr_stage(self) -> GraphicsStage | None:
        """GraphicsStage | None: scene containing the item."""
        return self.scene()

    @property
    def title_height(self) -> float:
        """float: height of the title."""
        return self.title_item.height

    @property
    def title_width(self) -> float:
        """float: width of the title."""
        return self.title_item.width

    @property
    def plugs(self) -> list[GraphicsPlug]:
        """list[GraphicsPlug]: plugs in display order."""
        return list(self._plugs.values())

    def get_plug(self, component) -> GraphicsPlug | None:
        """Get the plug of a component.

        Args:
            component (NodeComponent | UUID): component or its uuid.

        Returns:
            GraphicsPlug | None: plug, if the component has one.
        """
        return self._plugs.get(getattr(component, "uuid", component))

    # ======== Refresh and layout ========= #

    def refresh(self):
        """Re-read the node state and update the item to match it."""
        position = self._node.position()
        if position is not None and self.pos() != position:
            self.setPos(position)

        self.title_item.refresh()
        self._icon = QtGui.QIcon(self._node.get_type_icon())
        self._brush_background = QtGui.QBrush(
            self.REFERENCE_NODE_BACKGROUND
            if self._node.is_referenced
            else self.BACKGROUND_COLOR
        )
        self._sync_plugs()
        self.update_layout()
        self.update()

    def _sync_plugs(self):
        """Create, drop and refresh plugs so they match the node components."""
        components = [
            component
            for component in self._node.components_model.list_components()
            if GraphicsPlug.is_plug_component(component)
        ]
        wanted = {component.uuid for component in components}
        for uuid in list(self._plugs):
            plug = self._plugs[uuid]
            if uuid not in wanted or plug.component not in components:
                self._remove_plug(self._plugs.pop(uuid))

        plugs: dict[UUID, GraphicsPlug] = {}
        for component in components:
            plug = self._plugs.get(component.uuid)
            if plug is None:
                plug = GraphicsPlug(component, self)
            plug.refresh()
            plugs[component.uuid] = plug
        self._plugs = plugs

    def _remove_plug(self, plug: GraphicsPlug):
        """Remove a plug item from the scene.

        Args:
            plug (GraphicsPlug): plug to remove.
        """
        gr_stage = plug.scene()
        if gr_stage is not None:
            for link in plug.links:
                gr_stage.remove_link(link)
            gr_stage.removeItem(plug)
        plug.setParentItem(None)

    def update_layout(self):
        """Recompute size from the title and plugs, place children, rebuild paths."""
        self.prepareGeometryChange()
        self.width = max(
            self.MIN_WIDTH,
            self.TITLE_OFFSET_X + self.title_width + self.title_horizontal_padding,
        )
        plugs_top = self.title_height + self.plugs_top_padding
        for row, plug in enumerate(self._plugs.values()):
            plug.set_width(self.width)
            plug.setPos(0.0, plugs_top + row * GraphicsPlug.ROW_HEIGHT)
            plug.update_links()
        plugs_bottom = (
            plugs_top + len(self._plugs) * GraphicsPlug.ROW_HEIGHT + self.lower_padding
        )
        self.height = max(self.MIN_HEIGHT, plugs_bottom)
        self._rebuild_paths()

    def _rebuild_paths(self):
        """Rebuild the cached title, content and outline paths."""
        w, h, r = self.width, self.height, self.edge_roundness
        title_h = self.title_height

        title = QtGui.QPainterPath()
        title.setFillRule(QtCore.Qt.WindingFill)
        title.addRoundedRect(0, 0, w, title_h, r, r)
        title.addRect(0, title_h - r, r, r)
        title.addRect(w - r, title_h - r, r, r)
        self._path_title = title.simplified()

        content = QtGui.QPainterPath()
        content.setFillRule(QtCore.Qt.WindingFill)
        content.addRoundedRect(0, title_h, w, h - title_h, r, r)
        content.addRect(0, title_h, r, r)
        content.addRect(w - r, title_h, r, r)
        self._path_content = content.simplified()

        outline = QtGui.QPainterPath()
        outline.addRoundedRect(-1, -1, w + 2, h + 2, r, r)
        self._path_outline = outline.simplified()

    # ======== Painting ========= #

    def boundingRect(self) -> QtCore.QRectF:
        """QtCore.QRectF: bounds of the node, including the outline."""
        return QtCore.QRectF(-1, -1, self.width + 2, self.height + 2)

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionGraphicsItem,
        widget: QtWidgets.QWidget | None = None,
    ) -> None:
        """Draw the node body, title bar and icon.

        Args:
            painter (QtGui.QPainter): painter.
            option (QtWidgets.QStyleOptionGraphicsItem): style options.
            widget (QtWidgets.QWidget | None): painted widget.
        """
        # TODO: Adjust title visibility based on scale
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(self._brush_title)
        painter.drawPath(self._path_title)
        self._icon.paint(painter, self.ICON_RECT)

        painter.setBrush(self._brush_background)
        painter.drawPath(self._path_content)

        # TODO: Paint prominent outline if exec input is connected
        painter.setPen(
            self._pen_default if not self.isSelected() else self._pen_selected
        )
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawPath(self._path_outline)

    def _refresh_tooltip(self):
        """Show node role diagnostics as tooltip if enabled in config or debug mode."""
        if not self._node.index().isValid():
            return

        if are_hover_diagnostics_enabled():
            self.setToolTip(build_role_tooltip_html(self._node.index()))

    # ======== Events ========= #

    def mouseReleaseEvent(self, event):
        """Push a move command for the selected nodes that were moved.

        Args:
            event (QtWidgets.QGraphicsSceneMouseEvent): event.
        """
        super().mouseReleaseEvent(event)

        gr_stage = self.gr_stage
        if gr_stage is None:
            return

        moved_nodes = []
        new_positions = []
        for gr_node in gr_stage.selected_gr_nodes():
            if gr_node.pos() != gr_node.node.position():
                moved_nodes.append(gr_node.node)
                new_positions.append(gr_node.pos())

        if moved_nodes:
            move_cmd = commands.MoveNodeCommand(
                stage=self._node.stage, nodes=moved_nodes, new_positions=new_positions
            )
            self._node.stage.push_command(move_cmd)

    def itemChange(self, change, value):
        """Keep the links of the plugs attached to the node while it moves.

        Args:
            change (QtWidgets.QGraphicsItem.GraphicsItemChange): kind of change.
            value (typing.Any): new value.

        Returns:
            typing.Any: value to apply.
        """
        if change == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for plug in self._plugs.values():
                plug.update_links()
        return super().itemChange(change, value)

    def hoverEnterEvent(self, event: QtWidgets.QGraphicsSceneHoverEvent) -> None:
        """Refresh the tooltip when the cursor enters.

        Args:
            event (QtWidgets.QGraphicsSceneHoverEvent): event.
        """
        self._refresh_tooltip()
        super().hoverEnterEvent(event)
