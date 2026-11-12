from PySide6 import QtGui, QtWidgets

from nyx.core import Node


class NodeItemDelegate(QtWidgets.QStyledItemDelegate):
    """Renders stage nodes in item views.

    Single place for per-node item rendering. Currently provides the node type
    icon, read from the `Node.Roles.TYPE_ICON` role (a resource / file path).
    """

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        """Initialize NodeItemDelegate.

        Args:
            parent (QtCore.QObject | None): parent object.
        """
        super().__init__(parent)
        self._icon_cache: dict[str, QtGui.QIcon] = {}

    def initStyleOption(self, option: QtWidgets.QStyleOptionViewItem, index) -> None:
        """Show the node type icon as the item decoration.

        Args:
            option (QtWidgets.QStyleOptionViewItem): option to initialize.
            index (QtCore.QModelIndex): item index.
        """
        super().initStyleOption(option, index)
        icon_path = index.data(Node.Roles.TYPE_ICON)
        if not icon_path or not isinstance(icon_path, str):
            return

        icon = self._icon_for(icon_path)
        if icon.isNull():
            return
        option.icon = icon
        option.features |= QtWidgets.QStyleOptionViewItem.ViewItemFeature.HasDecoration

    def _icon_for(self, icon_path: str) -> QtGui.QIcon:
        """Get an icon, caching it by path.

        Args:
            icon_path (str): icon resource path.

        Returns:
            QtGui.QIcon: icon.
        """
        icon = self._icon_cache.get(icon_path)
        if icon is None:
            icon = QtGui.QIcon(icon_path)
            self._icon_cache[icon_path] = icon
        return icon
