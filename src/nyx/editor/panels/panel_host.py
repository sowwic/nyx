from __future__ import annotations

import enum

import shiboken6
from PySide6 import QtCore, QtGui, QtWidgets

from .overlay_panel import OverlayPanel
from .panel_registry import PanelArea
from .panel_sidebar import PanelSidebar


class _PanelCanvas(QtWidgets.QWidget):
    """Area the graph fills and the panels float over, laid out by the host."""

    resized = QtCore.Signal()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        """Ask the host to place the children.

        Args:
            event (QtGui.QResizeEvent): event.
        """
        super().resizeEvent(event)
        self.resized.emit()


class FloatingAnchor(enum.StrEnum):
    """Corner of the graph area a floating widget is attached to."""

    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"


class PanelHost(QtWidgets.QWidget):
    """Central widget: sidebar and the graph area with panels floating over it.

    Opening a panel never changes the size of the graph area. Panels start below the
    tab bar of the MDI area, so the tabs always stay reachable. Small widgets float in
    the corners of the space the panels leave free.
    """

    DEFAULT_SIZES = {
        PanelArea.LEFT: 320,
        PanelArea.RIGHT: 340,
        PanelArea.BOTTOM: 260,
    }
    MINIMUM_SIZES = {
        PanelArea.LEFT: 280,
        PanelArea.RIGHT: 330,
        PanelArea.BOTTOM: 155,
    }
    """Smallest width (height for the bottom area) a panel can be given."""
    MAXIMUM_FRACTIONS = {
        PanelArea.LEFT: 0.7,
        PanelArea.RIGHT: 0.7,
        PanelArea.BOTTOM: 0.9,
    }
    """Largest share of the graph area (its width, or height for the bottom area) a
    panel can take."""
    MINIMUM_FREE_SIZE = 60
    """Width (height for the bottom area) the panels leave free, while the minimum
    sizes of the open panels allow it."""
    FLOATING_MARGIN = 10
    FLOATING_SPACING = 6

    def __init__(
        self,
        mdi_area: QtWidgets.QMdiArea,
        sidebar: PanelSidebar,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        """Initialize PanelHost.

        Args:
            mdi_area (QtWidgets.QMdiArea): MDI area of the stage editors.
            sidebar (PanelSidebar): sidebar shown at the left.
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(parent)
        self.mdi_area = mdi_area
        self.sidebar = sidebar
        self._panels: list[OverlayPanel] = []
        self._sizes: dict[OverlayPanel, int] = {}
        self._floating: list[tuple[QtWidgets.QWidget, FloatingAnchor]] = []

        self._create_widgets()
        self._create_layouts()
        self._create_connections()

    def _create_widgets(self) -> None:
        """Create child widgets."""
        self.canvas = _PanelCanvas(self)
        self.mdi_area.setParent(self.canvas)
        self.mdi_area.show()

    def _create_layouts(self) -> None:
        """Create layouts."""
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.canvas, stretch=1)

    def _create_connections(self) -> None:
        """Create signal-slot connections."""
        self.canvas.resized.connect(self.update_layout)
        # The tab bar shows up with the first stage and goes with the last one
        self.mdi_area.subWindowActivated.connect(self._schedule_update_layout)

    def _schedule_update_layout(self, *_unused_signal_arguments) -> None:
        """Place the children on the next event-loop turn, once the tab bar settled."""
        # The host is the context, so the call is dropped if it is deleted meanwhile
        QtCore.QTimer.singleShot(0, self, self.update_layout)

    def attach_panel(self, panel: OverlayPanel, size: int | None = None) -> None:
        """Put a hidden panel over the graph area.

        Args:
            panel (OverlayPanel): panel to attach.
            size (int | None): width (height for the bottom area). Defaults to the
                standard size of the area.
        """
        panel.setParent(self.canvas)
        panel.hide()
        self._panels.append(panel)
        self.set_panel_size(panel, size or self.DEFAULT_SIZES[panel.area])

    def add_floating_widget(
        self,
        widget: QtWidgets.QWidget,
        anchor: FloatingAnchor = FloatingAnchor.TOP_RIGHT,
    ) -> None:
        """Put a small widget over a corner of the graph area.

        A corner is an anchor, not a single slot: widgets added to the same corner
        stack away from it in the order they were added. Hidden widgets take no room.

        The corners are those of the space the open panels leave free. Top corners are
        below the tab bar and bottom corners are above the bottom panel. When a right
        panel grows, right anchored widgets stop at the left panel and the right panel
        slides over them.

        Args:
            widget (QtWidgets.QWidget): widget to float.
            anchor (FloatingAnchor): corner to attach the widget to.
        """
        widget.setParent(self.canvas)
        widget.installEventFilter(self)
        widget.show()
        self._floating.append((widget, anchor))
        self.update_layout()

    def remove_floating_widget(self, widget: QtWidgets.QWidget) -> None:
        """Stop managing the position of a floating widget.

        Args:
            widget (QtWidgets.QWidget): widget that was added with
                `add_floating_widget`. Others are ignored.
        """
        widget.removeEventFilter(self)
        self._floating = [entry for entry in self._floating if entry[0] is not widget]
        self.update_layout()

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        """Stack the floating widgets again when one is shown, hidden or resized.

        Args:
            watched (QtCore.QObject): object that got the event.
            event (QtCore.QEvent): event.

        Returns:
            bool: always False, the event is not consumed.
        """
        if event.type() in (
            QtCore.QEvent.Type.Show,
            QtCore.QEvent.Type.Hide,
            QtCore.QEvent.Type.Resize,
        ) and any(widget is watched for widget, _ in self._floating):
            self._schedule_update_layout()
        return super().eventFilter(watched, event)

    def top_inset(self) -> int:
        """Get the height of the MDI tab bar, which panels must not cover.

        Returns:
            int: height in pixels, zero while there are no tabs.
        """
        tab_bar = self.mdi_area.findChild(QtWidgets.QTabBar)
        if tab_bar is None or tab_bar.isHidden():
            return 0
        return tab_bar.height()

    def panel_size(self, panel: OverlayPanel) -> int:
        """Get the requested size of a panel.

        Args:
            panel (OverlayPanel): attached panel.

        Returns:
            int: width, or height for the bottom area, in pixels.
        """
        return self._sizes[panel]

    def set_panel_size(self, panel: OverlayPanel, size: int) -> None:
        """Set the size of a panel and place it again.

        Args:
            panel (OverlayPanel): attached panel.
            size (int): width, or height for the bottom area, in pixels.
        """
        self._sizes[panel] = max(size, self.MINIMUM_SIZES[panel.area])
        self.update_layout()

    def _open_panel(self, area: PanelArea) -> OverlayPanel | None:
        """Get the open panel of an area.

        Args:
            area (PanelArea): area to look in.

        Returns:
            OverlayPanel | None: open panel, None if there is none.
        """
        for panel in self._panels:
            if panel.area is area and not panel.isHidden():
                return panel
        return None

    def _clamped_size(self, panel: OverlayPanel, extent: int, available: int) -> int:
        """Limit the size of a panel to its range, so the graph area stays visible.

        Args:
            panel (OverlayPanel): panel.
            extent (int): width of the graph area, or its height for the bottom area.
            available (int): part of the extent the panel can use, less than the extent
                when another panel is open at the other side.

        Returns:
            int: size in pixels, never below the minimum of the area.
        """
        minimum = self.MINIMUM_SIZES[panel.area]
        maximum = min(
            int(extent * self.MAXIMUM_FRACTIONS[panel.area]),
            available - self.MINIMUM_FREE_SIZE,
        )
        return min(self._sizes[panel], max(minimum, maximum))

    def update_layout(self) -> None:
        """Place the MDI area and the open panels inside the graph area."""
        width, height = self.canvas.width(), self.canvas.height()
        self.mdi_area.setGeometry(0, 0, width, height)

        top = self.top_inset()
        left = self._open_panel(PanelArea.LEFT)
        right = self._open_panel(PanelArea.RIGHT)
        bottom = self._open_panel(PanelArea.BOTTOM)

        # The left panel keeps its size, the right one takes what is left
        left_width = self._clamped_size(left, width, width) if left else 0
        right_width = (
            self._clamped_size(right, width, width - left_width) if right else 0
        )
        if left:
            left.setGeometry(0, top, left_width, height - top)
        if right:
            right.setGeometry(width - right_width, top, right_width, height - top)
        if bottom:
            bottom_height = self._clamped_size(bottom, height, height)
            bottom.setGeometry(
                left_width,
                height - bottom_height,
                max(width - left_width - right_width, 0),
                bottom_height,
            )
        self._place_floating_widgets(
            free_left=left_width,
            free_right=width - right_width,
            free_top=top,
            free_bottom=bottom.y() if bottom else height,
        )
        for panel in (left, right, bottom):
            if panel:
                panel.raise_()

    def _place_floating_widgets(
        self, free_left: int, free_right: int, free_top: int, free_bottom: int
    ) -> None:
        """Stack the floating widgets in the corners of the free space.

        Args:
            free_left (int): left edge of the space the panels leave free.
            free_right (int): right edge of that space.
            free_top (int): top edge of that space, below the tab bar.
            free_bottom (int): bottom edge of that space, above the bottom panel.
        """
        margin, spacing = self.FLOATING_MARGIN, self.FLOATING_SPACING
        # A widget can be deleted without being removed, for example a notification
        self._floating = [
            entry for entry in self._floating if shiboken6.isValid(entry[0])
        ]
        top_cursor = free_top + margin
        bottom_cursor = free_bottom - margin
        # Where the next widget of each corner goes: a top edge, or a bottom edge
        cursors = {
            FloatingAnchor.TOP_LEFT: top_cursor,
            FloatingAnchor.TOP_RIGHT: top_cursor,
            FloatingAnchor.BOTTOM_LEFT: bottom_cursor,
            FloatingAnchor.BOTTOM_RIGHT: bottom_cursor,
        }
        for widget, anchor in self._floating:
            if widget.isHidden():
                continue
            widget.adjustSize()
            if anchor in (FloatingAnchor.TOP_RIGHT, FloatingAnchor.BOTTOM_RIGHT):
                x = max(free_left + margin, free_right - margin - widget.width())
            else:
                x = free_left + margin
            if anchor in (FloatingAnchor.TOP_LEFT, FloatingAnchor.TOP_RIGHT):
                y = cursors[anchor]
                cursors[anchor] = y + widget.height() + spacing
            else:
                y = cursors[anchor] - widget.height()
                cursors[anchor] = y - spacing
            widget.move(x, y)
            widget.raise_()
