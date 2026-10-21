import dataclasses

from PySide6 import QtCore, QtGui

from ..static.enums import NodeExecutionStatus


@dataclasses.dataclass
class NodeRenderOptions:
    """How the editor draws a node type.

    Nodes return them from `Node.get_render_options`. A node type changes the look of
    its nodes by taking the default options from its parent class and tweaking them.

    Attributes:
        min_width: smallest width of the node
        min_plug_rows: the node is tall enough for this many plug rows, even with fewer
        shared_row_gap_trim: how much less gap there is between the labels of two
            plugs sharing a row
        title_color: color of the header
        background_color: color of the body
        reference_background_color: color of the body of a referenced node
        outline_color: color of the outline
        selected_outline_color: color of the outline of a selected node
        icon_rect: where the type icon is drawn in the header
        status_icon_rect: where the status icon is drawn, relative to the top right
            corner of the node
        status_icons: resource path of the icon of each execution status
        title_offset_x: distance of the title from the left side of the node
        subtitle_margin: space between the subtitle and the sides of the node
        edge_roundness: radius of the corners
        title_horizontal_padding: space after the title
        plugs_top_padding: space between the header and the first plug row
        lower_padding: space between the last plug row and the bottom of the node
    """

    min_width: float = 100.0
    min_plug_rows: int = 1
    shared_row_gap_trim: float = 12.0
    title_color: QtGui.QColor = dataclasses.field(
        default_factory=lambda: QtGui.QColor("#FF313131")
    )
    background_color: QtGui.QColor = dataclasses.field(
        default_factory=lambda: QtGui.QColor("#E3212121")
    )
    reference_background_color: QtGui.QColor = dataclasses.field(
        default_factory=lambda: QtGui.QColor("#2182CF")
    )
    outline_color: QtGui.QColor = dataclasses.field(
        default_factory=lambda: QtGui.QColor("#7F000000")
    )
    selected_outline_color: QtGui.QColor = dataclasses.field(
        default_factory=lambda: QtGui.QColor("#FFA637")
    )
    icon_rect: QtCore.QRect = dataclasses.field(
        default_factory=lambda: QtCore.QRect(8, 6, 16, 16)
    )
    status_icon_rect: QtCore.QRect = dataclasses.field(
        default_factory=lambda: QtCore.QRect(-7, -7, 14, 14)
    )
    status_icons: dict[NodeExecutionStatus, str] = dataclasses.field(
        default_factory=lambda: {
            NodeExecutionStatus.SUCCESS: ":/icons/green_check.png",
            NodeExecutionStatus.ERROR: ":/icons/red_error.png",
        }
    )
    title_offset_x: float = 28.0
    subtitle_margin: float = 8.0
    edge_roundness: float = 10.0
    title_horizontal_padding: float = 4.0
    plugs_top_padding: float = 4.0
    lower_padding: float = 8.0
