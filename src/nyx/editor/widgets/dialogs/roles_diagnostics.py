from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPersistentModelIndex, Qt
from PySide6.QtWidgets import QAbstractItemView, QDialog, QTableView, QVBoxLayout


class RoleDiagnosticsModel(QAbstractTableModel):
    """Table model listing every role of an index with its name and live value."""

    HEADERS = ("Role", "Name", "Value")

    def __init__(self, index: QModelIndex, parent=None):
        """Initialize RoleDiagnosticsModel.

        Args:
            index (QModelIndex): index to inspect.
            parent (QObject | None): parent object.
        """
        super().__init__(parent)
        self._index = QPersistentModelIndex(index)

        # roleNames() -> dict[int, QByteArray]; sort by role id for stable order
        names = index.model().roleNames()
        self._roles = sorted(
            (role, bytes(name.data()).decode()) for role, name in names.items()
        )

        # keep values live while the dialog is open
        index.model().dataChanged.connect(self._on_source_changed)

    def _on_source_changed(self, *args):
        """Refresh the value column when the inspected model changes."""
        if self._roles:
            self.dataChanged.emit(self.index(0, 2), self.index(len(self._roles) - 1, 2))

    def rowCount(self, parent=QModelIndex()):
        """Get the number of roles.

        Args:
            parent (QModelIndex): parent index.

        Returns:
            int: role count, 0 for a valid parent.
        """
        return 0 if parent.isValid() else len(self._roles)

    def columnCount(self, parent=QModelIndex()):
        """Get the number of columns.

        Args:
            parent (QModelIndex): parent index.

        Returns:
            int: column count, 0 for a valid parent.
        """
        return 0 if parent.isValid() else len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Get the column header text.

        Args:
            section (int): column.
            orientation (Qt.Orientation): header orientation.
            role (int): data role.

        Returns:
            str | None: header text for horizontal display headers.
        """
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.HEADERS[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        """Get the role id, name or current value for a cell.

        Args:
            index (QModelIndex): cell index.
            role (int): data role.

        Returns:
            Cell text or value, None for unsupported roles.
        """
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        role_id, role_name = self._roles[index.row()]
        col = index.column()
        if col == 0:
            return role_id
        if col == 1:
            return role_name
        if col == 2:
            if not self._index.isValid():
                return None
            value = self._index.data(role_id)  # goes through your data()
            return (
                "<invalid>"
                if value is None
                else repr(value)
                if not isinstance(value, str)
                else value
            )
        return None


class RoleDiagnisticsDialog(QDialog):
    """Dialog showing the roles of a model index in a table."""

    def __init__(self, index: QModelIndex, parent=None):
        """Initialize RoleDiagnisticsDialog.

        Args:
            index (QModelIndex): index to inspect.
            parent (QWidget | None): parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("Roles")
        self.resize(600, 500)

        view = QTableView(self)
        view.setModel(RoleDiagnosticsModel(index, view))
        view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        view.setSelectionBehavior(QAbstractItemView.SelectRows)
        view.verticalHeader().hide()
        view.horizontalHeader().setStretchLastSection(True)
        view.resizeColumnsToContents()

        layout = QVBoxLayout(self)
        layout.addWidget(view)
