import collections
import time
import typing

import shiboken6
from PySide6 import QtCore, QtGui, QtWidgets

from nyx.editor.graphics.graphics_link import GraphicsLink
from nyx.editor.graphics.graphics_node import GraphicsNode
from nyx.editor.graphics.graphics_plug import GraphicsPlug
from nyx.editor.graphics.level_of_detail import LevelOfDetail

if typing.TYPE_CHECKING:
    from nyx.editor.views.stage_graph_view import StageGraphView


class StageGraphDebugOverlay:
    """Performance and state numbers of a stage graph view, drawn over its corner.

    There is one overlay for the editor, attached to the view that is being worked in.
    The attached view reports every paint with `record_paint` and draws the overlay.

    The paint rate is the number of paints in the last second: a view that has nothing
    to redraw does not paint, so the rate drops to zero while it is idle.
    """

    WINDOW_SECONDS = 1.0
    MAX_SAMPLES = 240
    MARGIN = 8
    PADDING = 6
    FONT_FAMILIES = ["SF Mono", "Menlo", "Consolas", "DejaVu Sans Mono", "monospace"]
    """Monospaced fonts in order of preference, so the columns line up."""
    TEXT_COLOR = QtGui.QColor("#D8D8D8")
    BACKGROUND_COLOR = QtGui.QColor(0, 0, 0, 170)

    def __init__(self):
        """Initialize StageGraphDebugOverlay, attached to no view."""
        self._view: StageGraphView | None = None
        self._font = QtGui.QFont()
        self._font.setFamilies(self.FONT_FAMILIES)
        self._font.setStyleHint(QtGui.QFont.StyleHint.Monospace)
        self._font.setPointSize(9)
        # (time of the paint, seconds it took)
        self._paints: collections.deque[tuple[float, float]] = collections.deque(
            maxlen=self.MAX_SAMPLES
        )

    @property
    def view(self) -> StageGraphView | None:
        """StageGraphView | None: view the overlay describes and is drawn in."""
        return self._view

    def attach(self, view: StageGraphView | None):
        """Move the overlay to a view, taking it off the previous one.

        The paints of the previous view are forgotten.

        Args:
            view (StageGraphView | None): view to describe, None to show nowhere.
        """
        if view is self._view:
            return
        previous, self._view = self._view, view
        self._paints.clear()
        if previous is not None and shiboken6.isValid(previous):
            previous.debug_overlay = None
            previous.viewport().update()
        if view is not None:
            view.debug_overlay = self
            view.viewport().update()

    def record_paint(self, duration: float, now: float | None = None):
        """Remember a paint of the view.

        Args:
            duration (float): seconds the paint took.
            now (float | None): time of the paint, now if omitted.
        """
        self._paints.append((time.perf_counter() if now is None else now, duration))

    def paint_rate(self, now: float | None = None) -> int:
        """Get the paints of the view in the last second.

        Args:
            now (float | None): current time, now if omitted.

        Returns:
            int: number of paints.
        """
        now = time.perf_counter() if now is None else now
        return sum(1 for when, _ in self._paints if now - when <= self.WINDOW_SECONDS)

    def paint_times(self, now: float | None = None) -> tuple[float, float]:
        """Get how long the recent paints took.

        Args:
            now (float | None): current time, now if omitted.

        Returns:
            tuple[float, float]: duration in milliseconds of the last paint and the
                average of the paints in the last second. Zeros without paints.
        """
        now = time.perf_counter() if now is None else now
        recent = [d for when, d in self._paints if now - when <= self.WINDOW_SECONDS]
        if not recent:
            return 0.0, 0.0
        return self._paints[-1][1] * 1000, sum(recent) / len(recent) * 1000

    def lines(self, now: float | None = None) -> list[str]:
        """Describe the view.

        Args:
            now (float | None): current time, now if omitted.

        Returns:
            list[str]: lines of text to show, none while attached to no view.
        """
        view = self._view
        if view is None:
            return []
        gr_stage = view.gr_stage
        last_ms, average_ms = self.paint_times(now)
        scale = view.transform().m11()
        lod = LevelOfDetail.from_scale(
            scale,
            text_size=GraphicsPlug.LABEL_FONT.pointSizeF(),
            shape_size=GraphicsPlug.ROW_HEIGHT,
        )
        visible = view.items(view.viewport().rect())
        visible_nodes = self._count(visible, GraphicsNode)
        visible_links = self._count(visible, GraphicsLink)
        animator = gr_stage.pulse_animator
        pulses_active = len(animator.links_in_view()) if animator.is_running else 0
        pulses_skipped = len(animator.links) - pulses_active
        mouse = view.last_scene_mouse_pos
        size = view.viewport().size()
        return [
            f"paints/s  {self.paint_rate(now)}",
            f"paint     {last_ms:.1f} ms (avg {average_ms:.1f})",
            f"zoom      {view.zoom:.2f}  scale {scale * 100:.0f}%",
            f"detail    {lod.name}",
            f"nodes     {visible_nodes} / {len(gr_stage.gr_nodes())}",
            f"links     {visible_links} / {len(gr_stage.gr_links())}",
            f"plugs     {self._count(visible, GraphicsPlug)}",
            f"items     {len(visible)} / {len(gr_stage.items())}",
            f"pulsing   {pulses_active} ({pulses_skipped} skipped)",
            f"mouse     {mouse.x():.0f}, {mouse.y():.0f}",
            f"viewport  {size.width()}x{size.height()} @{view.devicePixelRatioF():g}x",
            f"mode      {view.interaction_mode.name}",
        ]

    @staticmethod
    def _count(items: list[QtWidgets.QGraphicsItem], item_type: type) -> int:
        """Count the items of a type.

        Args:
            items (list[QtWidgets.QGraphicsItem]): items to look through.
            item_type (type): type to count.

        Returns:
            int: number of items of the type.
        """
        return sum(1 for item in items if isinstance(item, item_type))

    def paint(self, painter: QtGui.QPainter):
        """Draw the numbers in the top left corner of the viewport.

        Args:
            painter (QtGui.QPainter): painter of the viewport.
        """
        lines = self.lines()
        if not lines:
            return
        painter.save()
        painter.resetTransform()
        painter.setFont(self._font)
        metrics = QtGui.QFontMetricsF(self._font)
        width = max(metrics.horizontalAdvance(line) for line in lines)
        box = QtCore.QRectF(
            self.MARGIN,
            self.MARGIN,
            width + 2 * self.PADDING,
            metrics.lineSpacing() * len(lines) + 2 * self.PADDING,
        )
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(self.BACKGROUND_COLOR)
        painter.drawRoundedRect(box, 4, 4)
        painter.setPen(self.TEXT_COLOR)
        for index, line in enumerate(lines):
            y = (
                box.top()
                + self.PADDING
                + metrics.ascent()
                + index * metrics.lineSpacing()
            )
            painter.drawText(QtCore.QPointF(box.left() + self.PADDING, y), line)
        painter.restore()
