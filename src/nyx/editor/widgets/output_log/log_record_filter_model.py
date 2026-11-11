import logging

from PySide6.QtCore import QModelIndex, QPersistentModelIndex, QSortFilterProxyModel

from nyx.core.models.log_record_model import LogRecordListModel


class LogRecordFilterModel(QSortFilterProxyModel):
    """Filters log records by minimum level and search text."""

    def __init__(self, parent=None):
        """Initialize LogRecordFilterModel.

        Args:
            parent (QObject | None): parent object.
        """
        super().__init__(parent)
        self._minimum_level = logging.NOTSET
        self._search_text = ""

    def set_minimum_level(self, minimum_level: int) -> None:
        """Only accept records at or above the level.

        Args:
            minimum_level (int): logging level number.
        """
        self.beginFilterChange()
        self._minimum_level = minimum_level
        self.endFilterChange()

    def set_search_text(self, search_text: str) -> None:
        """Only accept records whose message or logger name contains the text.

        Args:
            search_text (str): case-insensitive text, empty accepts everything.
        """
        self.beginFilterChange()
        self._search_text = search_text.strip().casefold()
        self.endFilterChange()

    def filterAcceptsRow(
        self, source_row: int, source_parent: QModelIndex | QPersistentModelIndex
    ) -> bool:
        """bool: record passes the level and text filters."""
        source_index = self.sourceModel().index(source_row, 0, source_parent)
        record: logging.LogRecord | None = source_index.data(
            LogRecordListModel.LogRecordRole
        )
        if record is None:
            return False
        if record.levelno < self._minimum_level:
            return False
        if not self._search_text:
            return True
        return (
            self._search_text in record.getMessage().casefold()
            or self._search_text in record.name.casefold()
        )
