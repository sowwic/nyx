import logging
from PySide6 import QtCore


class LogRecordListModel(QtCore.QAbstractListModel):
    LogRecordRole = QtCore.Qt.ItemDataRole.UserRole + 1

    def __init__(
        self,
        maximum_retained_log_record_count: int = 500,
        parent: QtCore.QObject | None = None,
    ):
        super().__init__(parent)
        self._maximum_retained_log_record_count = maximum_retained_log_record_count
        self._log_records: list[logging.LogRecord] = []

    # ---- Qt model interface ----
    def rowCount(
        self,
        parent_index: QtCore.QModelIndex
        | QtCore.QPersistentModelIndex = QtCore.QModelIndex(),
    ) -> int:
        return 0 if parent_index.isValid() else len(self._log_records)

    def data(
        self,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ):
        if not index.isValid():
            return None
        log_record = self._log_records[index.row()]
        if role == self.LogRecordRole:
            return log_record
        if role in (
            QtCore.Qt.ItemDataRole.DisplayRole,
            QtCore.Qt.ItemDataRole.ToolTipRole,
        ):
            return log_record.getMessage()
        return None

    # ---- Public API ----
    def append_log_record(self, log_record: logging.LogRecord) -> None:
        new_row_index = len(self._log_records)
        self.beginInsertRows(QtCore.QModelIndex(), new_row_index, new_row_index)
        self._log_records.append(log_record)
        self.endInsertRows()

        number_of_excess_log_records = (
            len(self._log_records) - self._maximum_retained_log_record_count
        )
        if number_of_excess_log_records > 0:
            self.beginRemoveRows(
                QtCore.QModelIndex(), 0, number_of_excess_log_records - 1
            )
            del self._log_records[:number_of_excess_log_records]
            self.endRemoveRows()

    def clear_log_records(self) -> None:
        self.beginResetModel()
        self._log_records.clear()
        self.endResetModel()

    def latest_log_record(self) -> logging.LogRecord | None:
        return self._log_records[-1] if self._log_records else None
