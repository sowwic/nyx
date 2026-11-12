import typing
import logging

from PySide6.QtCore import (
    QPoint,
    Qt,
    Signal,
)
from PySide6.QtGui import QAction, QGuiApplication, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListView,
    QMenu,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from nyx.utils import logging_fn
from nyx.core.models.log_record_model import LogRecordListModel
from nyx.editor.utils import context_menus
from .log_filter_bar import LogFilterBar
from .log_record_delegate import LogRecordItemDelegate, color_for_logging_level
from .log_record_filter_model import LogRecordFilterModel
from ..common_widgets import ElidedTextLabel, ClickableHeaderWidget

if typing.TYPE_CHECKING:
    from nyx.core.logger import NyxLogger


class OutputLogWidget(QWidget):
    """Collapsible log with a header showing the latest message.

    Attributes:
        expansion_state_changed: emitted with the new expansion state
    """

    expansion_state_changed = Signal(bool)

    def __init__(
        self,
        log_message_list_model: LogRecordListModel | None = None,
        parent: QWidget | None = None,
    ):
        """Initialize OutputLogWidget.

        Args:
            log_message_list_model (LogRecordListModel | None): model of log
                records. Created if omitted.
            parent (QWidget | None): parent widget.
        """
        super().__init__(parent)
        self._log_message_list_model = log_message_list_model or LogRecordListModel(
            parent=self
        )
        self._is_expanded = False

        self._create_actions()
        self._create_widgets()
        self._create_layouts()
        self._create_connections()

        self._refresh_latest_message_display()
        self._apply_expansion_state_to_child_widgets()
        self.set_logger()

    def _create_actions(self) -> None:
        """Create actions."""
        self._copy_action = QAction("Copy", self)
        self._copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        self._copy_action.setShortcutContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut
        )
        self._select_all_action = QAction("Select All", self)
        self._select_all_action.setShortcut(QKeySequence.StandardKey.SelectAll)
        self._select_all_action.setShortcutContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut
        )
        self._clear_action = QAction("Clear", self)

    def _create_widgets(self) -> None:
        """Create child widgets."""
        # Header row (always visible)
        self._header_widget = ClickableHeaderWidget(self)
        self._header_widget.setFixedHeight(self.fontMetrics().height() + 12)

        self._latest_severity_indicator_label = QLabel(self._header_widget)
        self._latest_severity_indicator_label.setFixedSize(10, 10)

        self._latest_message_label = ElidedTextLabel(self._header_widget)

        self._toggle_expansion_button = QToolButton(self._header_widget)
        self._toggle_expansion_button.setAutoRaise(True)

        # History (visible only when expanded)
        self._filter_bar = LogFilterBar(self)

        self._filter_model = LogRecordFilterModel(self)
        self._filter_model.setSourceModel(self._log_message_list_model)

        self._log_message_list_view = QListView(self)
        self._log_message_list_view.setModel(self._filter_model)
        self._log_message_list_view.setItemDelegate(LogRecordItemDelegate(self))
        self._log_message_list_view.setUniformItemSizes(True)
        self._log_message_list_view.setEditTriggers(QListView.EditTrigger.NoEditTriggers)
        self._log_message_list_view.setVerticalScrollMode(
            QListView.ScrollMode.ScrollPerPixel
        )
        self._log_message_list_view.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self._log_message_list_view.setFrameShape(QListView.Shape.NoFrame)
        self._log_message_list_view.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self._log_message_list_view.addAction(self._copy_action)
        self._log_message_list_view.addAction(self._select_all_action)

    def _create_layouts(self) -> None:
        """Create layouts."""
        header_layout = QHBoxLayout(self._header_widget)
        header_layout.setContentsMargins(8, 0, 4, 0)
        header_layout.setSpacing(8)
        header_layout.addWidget(self._toggle_expansion_button)
        header_layout.addWidget(self._latest_severity_indicator_label)
        header_layout.addWidget(self._latest_message_label, stretch=1)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self._header_widget)
        main_layout.addWidget(self._filter_bar)
        main_layout.addWidget(self._log_message_list_view, stretch=1)

    def _create_connections(self) -> None:
        """Create signal-slot connections."""
        self._toggle_expansion_button.clicked.connect(self.toggle_expanded_state)
        self._log_message_list_model.rowsInserted.connect(self._on_log_records_inserted)
        self._log_message_list_model.modelReset.connect(
            self._refresh_latest_message_display
        )
        self._filter_bar.search_text_changed.connect(self._on_search_text_changed)
        self._filter_bar.minimum_level_changed.connect(self._on_minimum_level_changed)
        self._filter_bar.clear_requested.connect(self._clear_action.trigger)
        self._log_message_list_view.customContextMenuRequested.connect(
            self._show_context_menu
        )
        self._copy_action.triggered.connect(self._copy_selected_records)
        self._select_all_action.triggered.connect(self._log_message_list_view.selectAll)
        self._clear_action.triggered.connect(
            self._log_message_list_model.clear_log_records
        )

    # ---- Public API ----
    def header_height_in_pixels(self) -> int:
        """int: height of the always visible header."""
        return self._header_widget.height()

    def is_expanded(self) -> bool:
        """bool: log list is shown."""
        return self._is_expanded

    def set_expanded(self, should_be_expanded: bool) -> None:
        """Show or hide the log list.

        Args:
            should_be_expanded (bool): whether the list is shown.
        """
        if should_be_expanded == self._is_expanded:
            return
        self._is_expanded = should_be_expanded
        self._apply_expansion_state_to_child_widgets()
        self.expansion_state_changed.emit(self._is_expanded)

    def get_minimum_level(self) -> int:
        """int: minimum logging level shown in the history."""
        return self._filter_bar.get_minimum_level()

    def set_minimum_level(self, minimum_level: int) -> None:
        """Set the minimum logging level shown in the history.

        Args:
            minimum_level (int): logging level number.
        """
        self._filter_bar.set_minimum_level(minimum_level)

    def toggle_expanded_state(self) -> None:
        """Toggle between expanded and collapsed."""
        self.set_expanded(not self._is_expanded)

    # ---- Internals ----
    def set_logger(self):
        """Feed the model with records from the root logger."""
        self._logger: NyxLogger = logging.getLogger()
        signal_handler = logging_fn.add_signal_handler(self._logger)
        # The signal carries a logging.LogRecord, so it can feed the model directly.
        # The model is a QObject living in the GUI thread, so records logged from
        # worker threads are delivered through a queued connection automatically.
        signal_handler.emitter.record_logged.connect(
            self._log_message_list_model.append_log_record
        )

    def _apply_expansion_state_to_child_widgets(self) -> None:
        """Show the list and arrow matching the expansion state."""
        self._log_message_list_view.setVisible(self._is_expanded)
        self._filter_bar.setVisible(self._is_expanded)
        self._toggle_expansion_button.setArrowType(
            Qt.ArrowType.DownArrow if self._is_expanded else Qt.ArrowType.UpArrow
        )
        if self._is_expanded:
            self._log_message_list_view.scrollToBottom()

    def _on_log_records_inserted(self, *_unused_signal_arguments) -> None:
        """Update the header and scroll to the newest record."""
        self._refresh_latest_message_display()
        self._log_message_list_view.scrollToBottom()

    def _on_search_text_changed(self, search_text: str) -> None:
        """Filter records by text."""
        self._filter_model.set_search_text(search_text)
        self._log_message_list_view.scrollToBottom()

    def _on_minimum_level_changed(self, minimum_level: int) -> None:
        """Filter records by level."""
        self._filter_model.set_minimum_level(minimum_level)
        self._log_message_list_view.scrollToBottom()

    def _copy_selected_records(self) -> None:
        """Copy the selected records to the clipboard, one line each."""
        selected_rows = sorted(
            self._log_message_list_view.selectionModel().selectedRows(),
            key=lambda index: index.row(),
        )
        lines = [
            logging_fn.format_log_record_message_as_single_line(
                index.data(LogRecordListModel.LogRecordRole)
            )
            for index in selected_rows
        ]
        QGuiApplication.clipboard().setText("\n".join(lines))

    def _show_context_menu(self, point: QPoint) -> None:
        """Show the log context menu.

        Args:
            point (QPoint): position in the list view's viewport.
        """
        has_selection = self._log_message_list_view.selectionModel().hasSelection()
        self._copy_action.setEnabled(has_selection)
        self._select_all_action.setEnabled(self._filter_model.rowCount() > 0)
        self._clear_action.setEnabled(self._log_message_list_model.rowCount() > 0)

        menu = QMenu(self)
        menu.addAction(self._copy_action)
        menu.addAction(self._select_all_action)
        menu.addSeparator()
        menu.addAction(self._clear_action)
        context_menus.show_menu(
            menu, self._log_message_list_view.viewport().mapToGlobal(point)
        )

    def _refresh_latest_message_display(self) -> None:
        """Show the latest record in the header, or "Ready" if there is none."""
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
