from PySide6 import QtCore, QtGui, QtWidgets


class PlaceholderPainter:
    """Paints a centred title and hint on a widget when it has no content."""

    def __init__(
        self,
        title: str,
        hint: str = "",
        title_extra_points: int = 10,
        hint_extra_points: int = 2,
        gap: int = 8,
    ):
        self.title = title
        self.hint = hint
        self.title_extra_points = title_extra_points
        self.hint_extra_points = hint_extra_points
        self.gap = gap

    def paint(self, widget: QtWidgets.QWidget, target: QtWidgets.QWidget | None = None):
        """Paint onto `target` (defaults to `widget`) using `widget`'s font and palette."""
        target = target or widget
        painter = QtGui.QPainter(target)
        painter.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing)
        rect = target.rect()

        base_font = widget.font()
        base_size = max(base_font.pointSizeF(), 10.0)

        title_font = QtGui.QFont(base_font)
        title_font.setPointSizeF(base_size + self.title_extra_points)
        title_font.setBold(True)

        hint_font = QtGui.QFont(base_font)
        hint_font.setPointSizeF(base_size + self.hint_extra_points)

        title_h = QtGui.QFontMetrics(title_font).height()
        hint_h = QtGui.QFontMetrics(hint_font).height() if self.hint else 0
        gap = self.gap if self.hint else 0
        top = rect.center().y() - (title_h + gap + hint_h) // 2

        text_color = widget.palette().color(QtGui.QPalette.ColorRole.WindowText)
        align = QtCore.Qt.AlignmentFlag.AlignCenter

        painter.setFont(title_font)
        painter.setPen(text_color)
        painter.drawText(
            QtCore.QRect(rect.left(), top, rect.width(), title_h), align, self.title
        )

        if self.hint:
            hint_color = QtGui.QColor(text_color)
            hint_color.setAlphaF(0.6)
            painter.setFont(hint_font)
            painter.setPen(hint_color)
            painter.drawText(
                QtCore.QRect(rect.left(), top + title_h + gap, rect.width(), hint_h),
                align,
                self.hint,
            )
        painter.end()
