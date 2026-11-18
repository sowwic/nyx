import typing
import logging

from PySide6.QtCore import (
    QPoint,
    Qt,
)
from PySide6.QtGui import QAction, QGuiApplication, QKeySequence, QShowEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QListView,
    QMenu,
    QVBoxLayout,
    QWidget,
)

from nyx.utils import logging_fn
from nyx.core.models.log_record_model import LogRecordListModel
from nyx.editor.utils import context_menus
from .log_filter_bar import LogFilterBar
from .log_record_delegate import LogRecordItemDelegate
from .log_record_filter_model import LogRecordFilterModel

if typing.TYPE_CHECKING:
    from nyx.core.logger import NyxLogger


class OutputLogWidget(QWidget):
    """Log of the records with a filter bar. It has no state of its own to show or hide.

    The panel it is a child of decides when it is visible.
    """

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

        self._create_actions()
        self._create_widgets()
        self._create_layouts()
        self._create_connections()

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
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self._filter_bar)
        main_layout.addWidget(self._log_message_list_view, stretch=1)

    def _create_connections(self) -> None:
        """Create signal-slot connections."""
        self._log_message_list_model.rowsInserted.connect(self._on_log_records_inserted)
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
    def get_minimum_level(self) -> int:
        """int: minimum logging level shown in the log."""
        return self._filter_bar.get_minimum_level()

    def set_minimum_level(self, minimum_level: int) -> None:
        """Set the minimum logging level shown in the log.

        Args:
            minimum_level (int): logging level number.
        """
        self._filter_bar.set_minimum_level(minimum_level)

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

    def showEvent(self, event: QShowEvent) -> None:
        """Show the newest records, which arrived while the log was hidden.

        Args:
            event (QShowEvent): event.
        """
        super().showEvent(event)
        self._log_message_list_view.scrollToBottom()

    def _on_log_records_inserted(self, *_unused_signal_arguments) -> None:
        """Scroll to the newest record."""
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
