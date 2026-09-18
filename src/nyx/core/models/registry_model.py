import typing
from collections import OrderedDict
from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt
from ..protocols.plugin_content import PluginContent


class RegistryListModel(QAbstractListModel):
    """Flat list model over a single registry dict: {type_id: cls}."""

    TypeIdRole = Qt.UserRole + 1
    ClassRole = Qt.UserRole + 2
    TagsRole = Qt.UserRole + 3

    def __init__(self, get_items: typing.Callable[[], OrderedDict], parent=None):
        """
        Args:
            get_items: callable returning current {type_id: cls} dict,
                       e.g. lambda: NYX_REGISTRY.nodes
        """
        super().__init__(parent)
        self._get_items = get_items
        self._type_ids: list[str] = []
        self._cls_by_id: dict[str, PluginContent] = {}
        self.rebuild()

    def rebuild(self):
        self.beginResetModel()
        self._cls_by_id = dict(self._get_items())
        self._type_ids = sorted(self._cls_by_id.keys())
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._type_ids)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        type_id = self._type_ids[index.row()]
        cls: PluginContent = self._cls_by_id[type_id]

        if role == Qt.DisplayRole:
            return cls.get_type_display_name()
        if role == self.TypeIdRole:
            return cls.get_type_id()
        if role == self.ClassRole:
            return cls
        if role == self.TagsRole:
            return cls.get_tags()
        return None

    def roleNames(self):
        return {
            Qt.DisplayRole: b"display",
            self.TypeIdRole: b"typeId",
            self.ClassRole: b"cls",
            self.TagsRole: b"tags",
        }
