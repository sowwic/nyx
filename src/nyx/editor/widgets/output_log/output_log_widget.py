import typing
import logging

from PySide6.QtCore import (
    Qt,
    Signal,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListView,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from nyx.utils import logging_fn
from nyx.core.models.log_record_model import LogRecordListModel
from .log_record_delegate import LogRecordItemDelegate, color_for_logging_level
from ..common_widgets import ElidedTextLabel, ClickableHeaderWidget

if typing.TYPE_CHECKING:
    from nyx.core.logger import NyxLogger


# --------------------------------------------------------------------------
# LogRecord helpers
# --------------------------------------------------------------------------


class OutputLogWidget(QWidget):
    expansion_state_changed = Signal(bool)

    def __init__(
        self,
        log_message_list_model: LogRecordListModel | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._log_message_list_model = log_message_list_model or LogRecordListModel(
            parent=self
        )
        self._is_expanded = False

        # ---- Header row (always visible) ----
        self._header_widget = ClickableHeaderWidget(self)
        self._header_widget.setFixedHeight(self.fontMetrics().height() + 12)

        self._latest_severity_indicator_label = QLabel(self._header_widget)
        self._latest_severity_indicator_label.setFixedSize(10, 10)

        self._latest_message_label = ElidedTextLabel(self._header_widget)

        self._toggle_expansion_button = QToolButton(self._header_widget)
        self._toggle_expansion_button.setAutoRaise(True)
        self._toggle_expansion_button.clicked.connect(self.toggle_expanded_state)

        header_layout = QHBoxLayout(self._header_widget)
        header_layout.setContentsMargins(8, 0, 4, 0)
        header_layout.setSpacing(8)
        header_layout.addWidget(self._toggle_expansion_button)
        header_layout.addWidget(self._latest_severity_indicator_label)
        header_layout.addWidget(self._latest_message_label, stretch=1)

        # ---- History list (visible only when expanded) ----
        self._log_message_list_view = QListView(self)
        self._log_message_list_view.setModel(self._log_message_list_model)
        self._log_message_list_view.setItemDelegate(LogRecordItemDelegate(self))
        self._log_message_list_view.setUniformItemSizes(True)
        self._log_message_list_view.setEditTriggers(QListView.EditTrigger.NoEditTriggers)
        self._log_message_list_view.setVerticalScrollMode(
            QListView.ScrollMode.ScrollPerPixel
        )
        self._log_message_list_view.setFrameShape(QListView.Shape.NoFrame)

        # ---- Layout ----
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self._header_widget)
        main_layout.addWidget(self._log_message_list_view, stretch=1)

        self._log_message_list_model.rowsInserted.connect(self._on_log_records_inserted)
        self._log_message_list_model.modelReset.connect(
            self._refresh_latest_message_display
        )

        self._refresh_latest_message_display()
        self._apply_expansion_state_to_child_widgets()
        self.set_logger()

    # ---- Public API ----
    def header_height_in_pixels(self) -> int:
        return self._header_widget.height()

    def is_expanded(self) -> bool:
        return self._is_expanded

    def set_expanded(self, should_be_expanded: bool) -> None:
        if should_be_expanded == self._is_expanded:
            return
        self._is_expanded = should_be_expanded
        self._apply_expansion_state_to_child_widgets()
        self.expansion_state_changed.emit(self._is_expanded)

    def toggle_expanded_state(self) -> None:
        self.set_expanded(not self._is_expanded)

    # ---- Internals ----
    def set_logger(self):
        self._logger: NyxLogger = logging.getLogger()
        signal_handler = logging_fn.add_signal_handler(self._logger)
        # The signal carries a logging.LogRecord, so it can feed the model directly.
        # The model is a QObject living in the GUI thread, so records logged from
        # worker threads are delivered through a queued connection automatically.
        signal_handler.emitter.record_logged.connect(
            self._log_message_list_model.append_log_record
        )

    def _apply_expansion_state_to_child_widgets(self) -> None:
        self._log_message_list_view.setVisible(self._is_expanded)
        self._toggle_expansion_button.setArrowType(
            Qt.ArrowType.DownArrow if self._is_expanded else Qt.ArrowType.UpArrow
        )
        if self._is_expanded:
            self._log_message_list_view.scrollToBottom()

    def _on_log_records_inserted(self, *_unused_signal_arguments) -> None:
        self._refresh_latest_message_display()
        self._log_message_list_view.scrollToBottom()

    def _refresh_latest_message_display(self) -> None:
        latest_log_record = self._log_message_list_model.latest_log_record()
        if latest_log_record is None:
            self._latest_message_label.set_full_text("Ready")
            self._latest_severity_indicator_label.setStyleSheet("")
            self._latest_severity_indicator_label.setVisible(False)
            return

        severity_color = color_for_logging_level(latest_log_record.levelno)
        self._latest_severity_indicator_label.setStyleSheet(
            f"background-color: {severity_color.name()}; border-radius: 5px;"
        )
        self._latest_severity_indicator_label.setVisible(True)
        self._latest_message_label.set_full_text(
            logging_fn.format_log_record_message_as_single_line(latest_log_record)
        )
