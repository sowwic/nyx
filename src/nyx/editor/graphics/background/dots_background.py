import math

from PySide6 import QtCore, QtGui

from nyx.core.stage_render_options import StageRenderOptions
from nyx.editor.graphics.background.stage_background import StageBackground


class DotsBackground(StageBackground):
    """A dot on every grid intersection.

    Dots are crisp squares that keep their size on screen, and are left out once
    they get too close.
    """

    def __init__(self, options: StageRenderOptions):
        super().__init__(options)
        self._pen = QtGui.QPen(options.dot_color)
        self._pen.setCapStyle(QtCore.Qt.PenCapStyle.SquareCap)

    def draw(self, painter, rect):
        grid_size = self.options.grid_size
        scale = painter.worldTransform().m11()
        if scale <= 0 or grid_size * scale < self.options.dots_min_spacing:
            return
        left = int(math.floor(rect.left()))
        top = int(math.floor(rect.top()))
        first_left = left - (left % grid_size)
        first_top = top - (top % grid_size)

        # Snap to whole pixels in view space and draw without antialiasing, dots
        # at fractional positions get smeared over neighbouring pixels
        transform = painter.worldTransform()
        points = [
            transform.map(QtCore.QPointF(x, y)).toPoint()
            for x in range(first_left, int(math.ceil(rect.right())) + 1, grid_size)
            for y in range(first_top, int(math.ceil(rect.bottom())) + 1, grid_size)
        ]
        self._pen.setWidth(max(1, round(self.options.dot_size)))
        painter.save()
        painter.resetTransform()
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, False)
        painter.setPen(self._pen)
        painter.drawPoints(points)
        painter.restore()
