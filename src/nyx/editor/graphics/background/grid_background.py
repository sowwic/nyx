import math

from PySide6 import QtCore, QtGui

from nyx.core.stage_render_options import StageRenderOptions
from nyx.editor.graphics.background.stage_background import StageBackground


class GridBackground(StageBackground):
    """Minor and major grid lines."""

    def __init__(self, options: StageRenderOptions):
        super().__init__(options)
        self._pen_light = QtGui.QPen(options.grid_light_color)
        self._pen_light.setWidth(options.grid_light_width)
        self._pen_dark = QtGui.QPen(options.grid_dark_color)
        self._pen_dark.setWidth(options.grid_dark_width)

    def draw(self, painter, rect):
        grid_size = self.options.grid_size
        major_size = grid_size * self.options.grid_squares
        left = int(math.floor(rect.left()))
        right = int(math.ceil(rect.right()))
        top = int(math.floor(rect.top()))
        bottom = int(math.ceil(rect.bottom()))

        first_left = left - (left % grid_size)
        first_top = top - (top % grid_size)

        # Compute line drawing
        lines_light, lines_dark = [], []
        for x in range(first_left, right, grid_size):
            if x % major_size:
                lines_light.append(QtCore.QLine(x, top, x, bottom))
            else:
                lines_dark.append(QtCore.QLine(x, top, x, bottom))

        for y in range(first_top, bottom, grid_size):
            if y % major_size:
                lines_light.append(QtCore.QLine(left, y, right, y))
            else:
                lines_dark.append(QtCore.QLine(left, y, right, y))

        # Draw lines
        painter.setPen(self._pen_light)
        painter.drawLines(lines_light)
        painter.setPen(self._pen_dark)
        painter.drawLines(lines_dark)
