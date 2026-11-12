import logging
from nyx.core.models.log_record_model import LogRecordListModel
from nyx.utils import logging_fn

from PySide6 import QtCore, QtGui, QtWidgets

INFORMATION_SEVERITY_COLOR = QtGui.QColor("#3e63dd")
WARNING_SEVERITY_COLOR = QtGui.QColor("#f5a524")
ERROR_SEVERITY_COLOR = QtGui.QColor("#e5484d")


def color_for_logging_level(logging_level: int) -> QtGui.QColor:
    """Threshold based, so custom levels (e.g. 25) still get a sensible colour."""
    if logging_level >= logging.ERROR:
        return ERROR_SEVERITY_COLOR
    if logging_level >= logging.WARNING:
        return WARNING_SEVERITY_COLOR
    return INFORMATION_SEVERITY_COLOR


class LogRecordItemDelegate(QtWidgets.QStyledItemDelegate):
    """Draws a log record row with a severity bar, level, time and message."""

    ROW_VERTICAL_PADDING_IN_PIXELS = 4
    SEVERITY_BAR_WIDTH_IN_PIXELS = 4
    HORIZONTAL_SPACING_IN_PIXELS = 10
    HORIZONTAL_MARGIN_IN_PIXELS = 8
    # The column is sized to the widest of these (in bold); other names are elided.
    EXPECTED_LEVEL_NAME_TEXTS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")

    def sizeHint(
        self,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
    ) -> QtCore.QSize:
        """Get the row size.

        Args:
            option (QtWidgets.QStyleOptionViewItem): style options.
            index (QtCore.QModelIndex | QtCore.QPersistentModelIndex): item index.

        Returns:
            QtCore.QSize: row size. The width is left to the view.
        """
        row_height_in_pixels = (
            option.fontMetrics.height() + 2 * self.ROW_VERTICAL_PADDING_IN_PIXELS
        )
        return QtCore.QSize(0, row_height_in_pixels)

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
    ) -> None:
        """Draw the log record row.

        Args:
            painter (QtGui.QPainter): painter.
            option (QtWidgets.QStyleOptionViewItem): style options.
            index (QtCore.QModelIndex | QtCore.QPersistentModelIndex): item index.
        """
        painter.save()

        is_row_selected = bool(option.state & QtWidgets.QStyle.StateFlag.State_Selected)
        if is_row_selected:
            painter.fillRect(option.rect, option.palette.highlight())
        text_color = (
            option.palette.highlightedText().color()
            if is_row_selected
            else option.palette.text().color()
        )

        log_record: logging.LogRecord = index.data(LogRecordListModel.LogRecordRole)
        severity_color = color_for_logging_level(log_record.levelno)
        timestamp_text = logging_fn.format_log_record_timestamp(log_record)
        level_name_text = log_record.levelname
        message_text = logging_fn.format_log_record_message_as_single_line(log_record)

        font_metrics: QtGui.QFontMetrics = option.fontMetrics
        row_rect: QtCore.QRect = option.rect

        # Coloured severity bar
        severity_bar_rect = QtCore.QRect(
            row_rect.left() + self.HORIZONTAL_MARGIN_IN_PIXELS,
            row_rect.top() + 2,
            self.SEVERITY_BAR_WIDTH_IN_PIXELS,
            row_rect.height() - 4,
        )
        painter.fillRect(severity_bar_rect, severity_color)

        current_x_position = (
            severity_bar_rect.right() + self.HORIZONTAL_SPACING_IN_PIXELS
        )

        # Timestamp
        timestamp_width_in_pixels = font_metrics.horizontalAdvance("00:00:00")
        timestamp_rect = QtCore.QRect(
            current_x_position,
            row_rect.top(),
            timestamp_width_in_pixels,
            row_rect.height(),
        )
        painter.setPen(text_color)
        painter.setOpacity(0.6)
        painter.drawText(
            timestamp_rect,
            QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignLeft,
            timestamp_text,
        )
        painter.setOpacity(1.0)
        current_x_position = timestamp_rect.right() + self.HORIZONTAL_SPACING_IN_PIXELS

        # Level name (bold; measured with the bold font, elided for odd custom names)
        bold_font = painter.font()
        bold_font.setBold(True)
        painter.setFont(bold_font)
        bold_font_metrics = QtGui.QFontMetrics(bold_font)
        level_name_width_in_pixels = max(
            bold_font_metrics.horizontalAdvance(expected_level_name_text)
            for expected_level_name_text in self.EXPECTED_LEVEL_NAME_TEXTS
        )
        level_name_rect = QtCore.QRect(
            current_x_position,
            row_rect.top(),
            level_name_width_in_pixels,
            row_rect.height(),
        )
        painter.setPen(severity_color if not is_row_selected else text_color)
        painter.drawText(
            level_name_rect,
            QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignLeft,
            bold_font_metrics.elidedText(
                level_name_text,
                QtCore.Qt.TextElideMode.ElideRight,
                level_name_rect.width(),
            ),
        )
        bold_font.setBold(False)
        painter.setFont(bold_font)
        current_x_position = level_name_rect.right() + self.HORIZONTAL_SPACING_IN_PIXELS

        # Message (elided; full text is available as the tooltip)
        message_rect = QtCore.QRect(
            current_x_position,
            row_rect.top(),
            max(
                0,
                row_rect.right() - self.HORIZONTAL_MARGIN_IN_PIXELS - current_x_position,
            ),
            row_rect.height(),
        )
        elided_message_text = font_metrics.elidedText(
            message_text, QtCore.Qt.TextElideMode.ElideRight, message_rect.width()
        )
        painter.setPen(text_color)
        painter.drawText(
            message_rect,
            QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignLeft,
            elided_message_text,
        )

        painter.restore()
