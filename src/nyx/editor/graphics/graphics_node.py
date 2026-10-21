import typing
from uuid import UUID

from PySide6 import QtCore, QtGui, QtWidgets

from .graphics_node_subtitle import GraphicsNodeSubtitle
from .graphics_node_title import GraphicsNodeTitle
from .graphics_plug import GraphicsPlug
from .level_of_detail import LevelOfDetail
from ..utils.common import build_role_tooltip_html, are_hover_diagnostics_enabled
from ...core import commands
from ...static.enums import NodeExecutionStatus

if typing.TYPE_CHECKING:
    from nyx.core import Node
    from nyx.core.node_render_options import NodeRenderOptions
    from nyx.editor.graphics.graphics_stage import GraphicsStage


class GraphicsNode(QtWidgets.QGraphicsItem):
    """Graphics item representing a node in the stage scene.

    The item is a view of its node: `refresh` re-reads everything from the node
    and `update_layout` recomputes the geometry. Geometry is only changed there.
    """

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
        self.options: NodeRenderOptions = node.get_render_options()
        self._plugs: dict[UUID, GraphicsPlug] = {}
        self._icon = QtGui.QIcon()
        self._status_pixmap: QtGui.QPixmap | None = None
        self._path_title = QtGui.QPainterPath()
        self._path_content = QtGui.QPainterPath()
        self._path_outline = QtGui.QPainterPath()

        self._init_sizes()
        self._init_assets()
        self.title_item = GraphicsNodeTitle(self)
        self.title_item.setPos(self.options.title_offset_x, 0)
        self.subtitle_item = GraphicsNodeSubtitle(self)

        self.refresh()

    def _init_sizes(self):
        """Initialize size values."""
        self.width = self.options.min_width
        self.height = 0.0  # set by update_layout

    def _init_assets(self):
        """Create the pens and brushes."""
        self._pen_default = QtGui.QPen(self.options.outline_color)
        self._pen_selected = QtGui.QPen(self.options.selected_outline_color)
        self._brush_title = QtGui.QBrush(self.options.title_color)
        self._brush_background = QtGui.QBrush(self.options.background_color)

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
        """float: height of the header: the title and the subtitle under it, if any."""
        return self.title_item.height + self.subtitle_item.height

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
        self.subtitle_item.refresh(self._node.subtitle)
        self._icon = QtGui.QIcon(self._node.get_type_icon())
        self._status_pixmap = self._build_status_pixmap(self._node.execution_status)
        self._brush_background = QtGui.QBrush(
            self.options.reference_background_color
            if self._node.is_referenced
            else self.options.background_color
        )
        self._sync_plugs()
        self.update_layout()
        self.update()

    def _build_status_pixmap(self, status: NodeExecutionStatus) -> QtGui.QPixmap | None:
        """Load the icon of an execution status.

        Args:
            status (NodeExecutionStatus): execution status.

        Returns:
            QtGui.QPixmap | None: tinted icon, None if the status has no icon.
        """
        qrc_path = self.options.status_icons.get(status)
        if qrc_path is None:
            return None
        pixmap = QtGui.QPixmap(qrc_path)
        if pixmap.isNull():
            return None
        painter = QtGui.QPainter(pixmap)
        painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceIn)
        painter.end()
        return pixmap

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

    def _arrange_plug_rows(
        self,
    ) -> list[tuple[GraphicsPlug | None, GraphicsPlug | None]]:
        """Distribute the plugs over rows, input sockets left and output sockets right.

        A plug takes only the sides it has a socket for. An input only plug and an
        output only plug share a row, a plug with both sockets has a row to itself.

        Returns:
            list[tuple[GraphicsPlug | None, GraphicsPlug | None]]: left (input) and
                right (output) plug of every row, in display order.
        """
        left_plugs: dict[int, GraphicsPlug] = {}
        right_plugs: dict[int, GraphicsPlug] = {}
        full_rows: set[int] = set()
        row_count = 0
        for plug in self._plugs.values():
            if plug.is_writable and plug.is_readable:
                full_rows.add(row_count)
                left_plugs[row_count] = plug
                row_count += 1
                continue
            slots = left_plugs if plug.is_writable else right_plugs
            row = next(
                (
                    row
                    for row in range(row_count)
                    if row not in full_rows and row not in slots
                ),
                row_count,
            )
            slots[row] = plug
            row_count = max(row_count, row + 1)
        return [(left_plugs.get(row), right_plugs.get(row)) for row in range(row_count)]

    def _row_width(self, row: tuple[GraphicsPlug | None, GraphicsPlug | None]) -> float:
        """Get the width a row of plugs needs.

        Args:
            row (tuple[GraphicsPlug | None, GraphicsPlug | None]): left and right plug.

        Returns:
            float: sum of the preferred widths, less the trim when two plugs share
                the row.
        """
        plugs = [plug for plug in row if plug is not None]
        width = sum(plug.preferred_width() for plug in plugs)
        return width - self.options.shared_row_gap_trim if len(plugs) == 2 else width

    def update_layout(self):
        """Recompute size from the title and plugs, place children, rebuild paths."""
        self.prepareGeometryChange()
        plug_rows = self._arrange_plug_rows()
        self.width = max(
            self.options.min_width,
            self.options.title_offset_x
            + self.title_width
            + self.options.title_horizontal_padding,
            self.subtitle_item.width + 2 * self.options.subtitle_margin,
            *(self._row_width(row) for row in plug_rows),
        )
        # Right aligned: the subtitle ends where the node does, the title starts at it
        self.subtitle_item.setPos(
            self.width - self.options.subtitle_margin - self.subtitle_item.width,
            self.title_item.height - self.subtitle_item.TITLE_OVERLAP,
        )
        plugs_top = self.title_height + self.options.plugs_top_padding
        for row, (left, right) in enumerate(plug_rows):
            y = plugs_top + row * GraphicsPlug.ROW_HEIGHT
            if left is not None and right is not None:
                # Gap between the two labels: the padding every plug keeps on its inner
                # side (see `GraphicsPlug.preferred_width`) plus the spare room of the
                # row, split evenly. The trim takes some of the padding away so the
                # labels sit closer, `_row_width` leaves out the same amount.
                spare = self.width - self._row_width((left, right))
                left_width = (
                    left.preferred_width()
                    - self.options.shared_row_gap_trim / 2
                    + spare / 2
                )
                left.set_width(left_width)
                left.setPos(0.0, y)
                right.set_width(self.width - left_width)
                right.setPos(left_width, y)
            else:
                plug = left or right
                plug.set_width(self.width)
                plug.setPos(0.0, y)
            for plug in (left, right):
                if plug is not None:
                    plug.update_links()
        self.height = (
            plugs_top
            + max(len(plug_rows), self.options.min_plug_rows) * GraphicsPlug.ROW_HEIGHT
            + self.options.lower_padding
        )
        self._rebuild_paths()

    def _rebuild_paths(self):
        """Rebuild the cached title, content and outline paths."""
        w, h, r = self.width, self.height, self.options.edge_roundness
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
        margin = -self.options.status_icon_rect.x()
        return QtCore.QRectF(
            -margin, -margin, self.width + 2 * margin, self.height + 2 * margin
        )

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
        lod = LevelOfDetail.from_painter(painter, shape_size=GraphicsPlug.ROW_HEIGHT)
        painter.setPen(QtCore.Qt.NoPen)
        if not lod.shows_shapes:
            self._paint_placeholder(painter)
            return

        painter.setBrush(self._brush_title)
        painter.drawPath(self._path_title)
        self._icon.paint(painter, self.options.icon_rect)

        painter.setBrush(self._brush_background)
        painter.drawPath(self._path_content)

        # TODO: Paint prominent outline if exec input is connected
        painter.setPen(
            self._pen_default if not self.isSelected() else self._pen_selected
        )
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawPath(self._path_outline)

        if self._status_pixmap is not None:
            painter.drawPixmap(self.options.status_icon_rect, self._status_pixmap)

    def _paint_placeholder(self, painter: QtGui.QPainter):
        """Draw the node as a flat rect, for when it is too small to see details.

        Args:
            painter (QtGui.QPainter): painter, without a pen.
        """
        painter.setBrush(self._brush_background)
        painter.drawRect(QtCore.QRectF(0.0, 0.0, self.width, self.height))
        if self.isSelected():
            painter.setPen(self._pen_selected)
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawRect(self.boundingRect())

    def _refresh_tooltip(self):
        """Show node role diagnostics as tooltip if enabled in config or debug mode, the
        description of the node type otherwise."""
        if not self._node.index().isValid():
            return

        if are_hover_diagnostics_enabled():
            self.setToolTip(build_role_tooltip_html(self._node.index()))
        else:
            self.setToolTip(self._node.get_description())

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
        elif change == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.update()
        return super().itemChange(change, value)

    def hoverEnterEvent(self, event: QtWidgets.QGraphicsSceneHoverEvent) -> None:
        """Refresh the tooltip when the cursor enters.

        Args:
            event (QtWidgets.QGraphicsSceneHoverEvent): event.
        """
        self._refresh_tooltip()
        super().hoverEnterEvent(event)
