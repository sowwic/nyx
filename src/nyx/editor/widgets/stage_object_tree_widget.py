from __future__ import annotations

import typing
from uuid import UUID

from PySide6 import QtCore, QtGui, QtWidgets

from nyx.core.node import Node
from nyx.core.node_component import NodeComponent
from nyx.editor.views.tree_branch_lines import BranchLinesMixin

if typing.TYPE_CHECKING:
    from nyx.core.stage import Stage


class StageObjectTreeWidget(BranchLinesMixin, QtWidgets.QTreeWidget):
    """Tree widget for browsing the objects of a stage and picking one.

    The rows are the nodes of the stage, with their components below them, each with the
    icon of its type, and the lines between the rows show which belongs to which. What
    the caller can't use is listed but can't be chosen, see `target_types` and
    `excluded`.

    Attributes:
        object_activated: emitted when an object that can be chosen is double clicked
    """

    COLUMNS = ("Name", "Path", "Type")
    UUID_ROLE = QtCore.Qt.ItemDataRole.UserRole + 1
    ICON_SIZE = QtCore.QSize(16, 16)

    object_activated = QtCore.Signal()

    def __init__(
        self,
        stage: Stage,
        target_types: tuple[type, ...] = (Node, NodeComponent),
        excluded: typing.Iterable[Node | NodeComponent] = (),
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        """Initialize StageObjectTreeWidget.

        Args:
            stage (Stage): stage to list.
            target_types (tuple[type, ...]): what can be chosen, `Node` and
                `NodeComponent`. Components are not listed when it has no
                `NodeComponent`.
            excluded (typing.Iterable[Node | NodeComponent]): objects that are listed
                but can't be chosen, like the component that is being filled.
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(parent)
        self._stage = stage
        self._target_types = target_types
        self._excluded_uuids = {each.uuid for each in excluded}
        self._items: dict[UUID, QtWidgets.QTreeWidgetItem] = {}
        self._icon_cache: dict[str, QtGui.QIcon] = {}

        self.setColumnCount(len(self.COLUMNS))
        self.setHeaderLabels(list(self.COLUMNS))
        self.setUniformRowHeights(True)
        self.setIconSize(self.ICON_SIZE)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)

        self._fill()
        self.itemDoubleClicked.connect(self._on_item_double_clicked)

    @property
    def selected_object(self) -> Node | NodeComponent | None:
        """Node | NodeComponent | None: the chosen object, None if there is none."""
        item = self.currentItem()
        if item is None or not self.is_selectable(item):
            return None
        return self._stage.uuid_map.get(item.data(0, self.UUID_ROLE))

    def item_for(
        self, stage_object: Node | NodeComponent
    ) -> QtWidgets.QTreeWidgetItem | None:
        """Get the item of an object.

        Args:
            stage_object (Node | NodeComponent): object.

        Returns:
            QtWidgets.QTreeWidgetItem | None: item, None if the object is not listed.
        """
        return self._items.get(stage_object.uuid)

    def listed_items(self) -> list[QtWidgets.QTreeWidgetItem]:
        """list[QtWidgets.QTreeWidgetItem]: the item of every object that is listed."""
        return list(self._items.values())

    @staticmethod
    def is_selectable(item: QtWidgets.QTreeWidgetItem) -> bool:
        """Check if an item can be chosen.

        Args:
            item (QtWidgets.QTreeWidgetItem): item.

        Returns:
            bool: True if the item can be chosen.
        """
        return bool(item.flags() & QtCore.Qt.ItemFlag.ItemIsSelectable)

    def select_object(self, stage_object: Node | NodeComponent | None) -> None:
        """Select an object and show it, if it is listed and can be chosen.

        Args:
            stage_object (Node | NodeComponent | None): object to select.
        """
        item = self.item_for(stage_object) if stage_object else None
        if item is None or not self.is_selectable(item):
            return
        self.setCurrentItem(item)
        self.scrollToItem(item)

    def filter_by_text(self, text: str) -> None:
        """Show the items matching a search, and what leads to them.

        Args:
            text (str): search text, everything is shown when it is empty.
        """
        text = text.strip().lower()
        root = self.invisibleRootItem()
        for index in range(root.childCount()):
            self._filter_item(root.child(index), text)

    # Building

    def _fill(self) -> None:
        """List the nodes of the stage with their components."""
        self._add_node(self.invisibleRootItem(), self._stage.root_node)
        self.expandToDepth(1)
        for column in range(len(self.COLUMNS)):
            self.resizeColumnToContents(column)

    def _add_node(self, parent_item: QtWidgets.QTreeWidgetItem, node: Node) -> None:
        """Add a node, its components and its children below an item.

        Args:
            parent_item (QtWidgets.QTreeWidgetItem): item to add below.
            node (Node): node to add.
        """
        item = self._make_item(parent_item, node)
        if any(issubclass(each, NodeComponent) for each in self._target_types):
            for component in node.components_model.list_components():
                self._make_item(item, component)
        for child in node.list_children():
            self._add_node(item, child)

    def _make_item(
        self,
        parent_item: QtWidgets.QTreeWidgetItem,
        stage_object: Node | NodeComponent,
    ) -> QtWidgets.QTreeWidgetItem:
        """Create the item of a stage object.

        Args:
            parent_item (QtWidgets.QTreeWidgetItem): item to add below.
            stage_object (Node | NodeComponent): object the item stands for.

        Returns:
            QtWidgets.QTreeWidgetItem: new item, which holds the uuid of the object.
        """
        item = QtWidgets.QTreeWidgetItem(
            parent_item,
            [
                stage_object.label,
                stage_object.path.as_posix(),
                stage_object.get_type_display_name(),
            ],
        )
        item.setIcon(0, self._icon_for(stage_object.get_type_icon()))
        item.setData(0, self.UUID_ROLE, stage_object.uuid)
        self._set_selectable(
            item,
            isinstance(stage_object, self._target_types)
            and stage_object.uuid not in self._excluded_uuids,
        )
        self._items[stage_object.uuid] = item
        return item

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

    @staticmethod
    def _set_selectable(item: QtWidgets.QTreeWidgetItem, selectable: bool) -> None:
        """Allow or forbid choosing an item. It stays visible and can be expanded.

        Args:
            item (QtWidgets.QTreeWidgetItem): item.
            selectable (bool): the item can be chosen.
        """
        flags = item.flags() | QtCore.Qt.ItemFlag.ItemIsEnabled
        if selectable:
            flags |= QtCore.Qt.ItemFlag.ItemIsSelectable
        else:
            flags &= ~QtCore.Qt.ItemFlag.ItemIsSelectable
        item.setFlags(flags)

    # Behaviour

    def _filter_item(self, item: QtWidgets.QTreeWidgetItem, text: str) -> bool:
        """Show or hide an item and its children for a search.

        Args:
            item (QtWidgets.QTreeWidgetItem): item to filter.
            text (str): lowercase search text, empty for no filtering.

        Returns:
            bool: the item is shown, because it or one of its children matches.
        """
        matches = not text or any(
            text in item.text(column).lower() for column in range(len(self.COLUMNS))
        )
        child_matches = False
        for index in range(item.childCount()):
            child_matches |= self._filter_item(item.child(index), text)
        item.setHidden(not (matches or child_matches))
        if text and child_matches:
            item.setExpanded(True)
        return matches or child_matches

    def _on_item_double_clicked(self, item: QtWidgets.QTreeWidgetItem) -> None:
        """Emit `object_activated` for a double clicked item that can be chosen.

        Args:
            item (QtWidgets.QTreeWidgetItem): item.
        """
        if self.is_selectable(item):
            self.object_activated.emit()
