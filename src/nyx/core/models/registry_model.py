import typing
import enum
from collections import OrderedDict

from PySide6 import QtCore

from ..protocols.registry_entry import IRegistryEntry
from ...utils.names_fn import enum_to_dict


class RegistryListModel(QtCore.QAbstractListModel):
    """Flat list model over a single registry dict: {type_id: cls}."""

    countChanged = QtCore.Signal()

    class Roles(enum.IntEnum):
        """Data roles exposed by the model."""

        TYPE_ID = QtCore.Qt.ItemDataRole.UserRole + 1
        TYPE_CLASS = enum.auto()
        TYPE_DISPLAY_NAME = enum.auto()
        TYPE_ICON = enum.auto()
        DESCRIPTION = enum.auto()
        TYPE_TAGS = enum.auto()

    def __init__(self, get_items: typing.Callable[[], OrderedDict], parent=None):
        """Initialize RegistryListModel.

        Args:
            get_items: callable returning current {type_id: cls} dict,
                       e.g. lambda: NYX_REGISTRY.nodes
            parent (QtCore.QObject | None): parent object.
        """
        super().__init__(parent)
        self._get_items = get_items
        self._type_ids: list[str] = []
        self._cls_by_id: dict[str, IRegistryEntry] = {}
        self.rebuild()

    @QtCore.Property(int, notify=countChanged)
    def count(self) -> int:
        """int: number of registry entries."""
        return len(self._get_items())

    def rebuild(self):
        """Reload entries from the registry."""
        self.beginResetModel()
        self._cls_by_id = dict(self._get_items())
        self._type_ids = sorted(self._cls_by_id.keys())
        self.endResetModel()

    def rowCount(self, parent=QtCore.QModelIndex()):
        """Get the number of entries.

        Args:
            parent: parent index.

        Returns:
            int: entry count, 0 for a valid parent.
        """
        if parent.isValid():
            return 0
        return len(self._type_ids)

    def data(self, index, role=QtCore.Qt.ItemDataRole.DisplayRole):
        """Get entry data.

        Args:
            index (QtCore.QModelIndex): item index.
            role: data role.

        Returns:
            Value for the role, None if unsupported.
        """
        if not index.isValid():
            return None
        type_id = self._type_ids[index.row()]
        cls: IRegistryEntry = self._cls_by_id[type_id]

        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            return cls.get_type_display_name()
        if role == self.Roles.TYPE_DISPLAY_NAME:
            return cls.get_type_display_name()
        if role == self.Roles.TYPE_ID:
            return cls.get_type_id()
        if role == self.Roles.TYPE_CLASS:
            return cls
        if role == self.Roles.TYPE_ICON:
            return cls.get_type_icon()
        if role == self.Roles.DESCRIPTION:
            return cls.get_description()
        if role == self.Roles.TYPE_TAGS:
            return cls.get_tags()
        return None

    def roleNames(self):
        """dict: role names exposed to QML."""
        return enum_to_dict(self.Roles)
