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
        TYPE_ID = QtCore.Qt.ItemDataRole.UserRole + 1
        TYPE_CLASS = enum.auto()
        TYPE_DISPLAY_NAME = enum.auto()
        TYPE_TAGS = enum.auto()

    def __init__(self, get_items: typing.Callable[[], OrderedDict], parent=None):
        """
        Args:
            get_items: callable returning current {type_id: cls} dict,
                       e.g. lambda: NYX_REGISTRY.nodes
        """
        super().__init__(parent)
        self._get_items = get_items
        self._type_ids: list[str] = []
        self._cls_by_id: dict[str, IRegistryEntry] = {}
        self.rebuild()

    @QtCore.Property(int, notify=countChanged)
    def count(self) -> int:
        return len(self._get_items())

    def rebuild(self):
        self.beginResetModel()
        self._cls_by_id = dict(self._get_items())
        self._type_ids = sorted(self._cls_by_id.keys())
        self.endResetModel()

    def rowCount(self, parent=QtCore.QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._type_ids)

    def data(self, index, role=QtCore.Qt.ItemDataRole.DisplayRole):
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
        if role == self.Roles.TYPE_TAGS:
            return cls.get_tags()
        return None

    def roleNames(self):
        return enum_to_dict(self.Roles)
