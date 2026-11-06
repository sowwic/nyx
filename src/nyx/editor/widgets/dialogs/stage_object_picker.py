from __future__ import annotations

import typing
from uuid import UUID

from PySide6 import QtCore, QtWidgets

from nyx.core.node import Node
from nyx.core.node_component import NodeComponent

if typing.TYPE_CHECKING:
    from nyx.core.stage import Stage


class StageObjectPickerDialog(QtWidgets.QDialog):
    """Dialog to choose a node or a component from a searchable tree of the stage.

    Nodes are listed with their components below them. What the caller can't use is
    shown but can't be chosen, see `target_types`.
    """

    COLUMNS = ("Name", "Path", "Type")
    UUID_ROLE = QtCore.Qt.ItemDataRole.UserRole + 1

    def __init__(
        self,
        stage: Stage,
        target_types: tuple[type, ...] = (Node, NodeComponent),
        current_target: Node | NodeComponent | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        """Initialize StageObjectPickerDialog.

        Args:
            stage (Stage): stage to choose from.
            target_types (tuple[type, ...]): what can be chosen, `Node` and
                `NodeComponent`. Components are not listed when it has no
                `NodeComponent`.
            current_target (Node | NodeComponent | None): object to start at.
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("Select stage object")
        self.resize(640, 480)
        self._stage = stage
        self._target_types = target_types
        self._items: dict[UUID, QtWidgets.QTreeWidgetItem] = {}

        self.search_field = QtWidgets.QLineEdit(self)
        self.search_field.setPlaceholderText("Search")
        self.search_field.setClearButtonEnabled(True)
        self.tree = QtWidgets.QTreeWidget(self)
        self.tree.setColumnCount(len(self.COLUMNS))
        self.tree.setHeaderLabels(list(self.COLUMNS))
        self.tree.setUniformRowHeights(True)
        self.tree.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )
        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel,
            self,
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.search_field)
        layout.addWidget(self.tree)
        layout.addWidget(self.buttons)

        self._fill_tree()
        self.search_field.textChanged.connect(self._apply_filter)
        self.tree.itemSelectionChanged.connect(self._update_ok_button)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        self._select(current_target)
        self._update_ok_button()
        self.search_field.setFocus()

    @classmethod
    def pick(
        cls,
        stage: Stage,
        component: NodeComponent,
        parent: QtWidgets.QWidget | None = None,
    ) -> Node | NodeComponent | None:
        """Ask the user for the object a path component should point at.

        Args:
            stage (Stage): stage to choose from.
            component (NodeComponent): path component being filled, tells what may be
                chosen (`target_types`) and where to start (`target`).
            parent (QtWidgets.QWidget | None): parent widget.

        Returns:
            Node | NodeComponent | None: chosen object, None if the dialog was
                cancelled.
        """
        dialog = cls(
            stage,
            target_types=getattr(component, "target_types", (Node, NodeComponent)),
            current_target=getattr(component, "target", None),
            parent=parent,
        )
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            return dialog.selected_object
        return None

    @property
    def selected_object(self) -> Node | NodeComponent | None:
        """Node | NodeComponent | None: the chosen object, None if there is none."""
        item = self.tree.currentItem()
        if item is None or not self._is_selectable(item):
            return None
        return self._stage.uuid_map.get(item.data(0, self.UUID_ROLE))

    # Building

    def _fill_tree(self) -> None:
        """List the nodes of the stage with their components."""
        self._add_node(self.tree.invisibleRootItem(), self._stage.root_node)
        self.tree.expandToDepth(1)
        for column in range(len(self.COLUMNS)):
            self.tree.resizeColumnToContents(column)

    def _add_node(self, parent_item: QtWidgets.QTreeWidgetItem, node: Node) -> None:
        """Add a node, its components and its children below an item.

        Args:
            parent_item (QtWidgets.QTreeWidgetItem): item to add below.
            node (Node): node to add.
        """
        item = self._make_item(parent_item, node, node.get_type_display_name())
        self._set_selectable(item, isinstance(node, self._target_types))
        if any(issubclass(each, NodeComponent) for each in self._target_types):
            for component in node.components_model.list_components():
                component_item = self._make_item(
                    item, component, component.get_type_display_name()
                )
                self._set_selectable(
                    component_item, isinstance(component, self._target_types)
                )
        for child in node.list_children():
            self._add_node(item, child)

    def _make_item(
        self,
        parent_item: QtWidgets.QTreeWidgetItem,
        stage_object: Node | NodeComponent,
        type_name: str,
    ) -> QtWidgets.QTreeWidgetItem:
        """Create the item of a stage object.

        Args:
            parent_item (QtWidgets.QTreeWidgetItem): item to add below.
            stage_object (Node | NodeComponent): object the item stands for.
            type_name (str): type name to show.

        Returns:
            QtWidgets.QTreeWidgetItem: new item, which holds the uuid of the object.
        """
        item = QtWidgets.QTreeWidgetItem(
            parent_item,
            [stage_object.label, stage_object.path.as_posix(), type_name],
        )
        item.setData(0, self.UUID_ROLE, stage_object.uuid)
        self._items[stage_object.uuid] = item
        return item

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

    @staticmethod
    def _is_selectable(item: QtWidgets.QTreeWidgetItem) -> bool:
        """bool: the item can be chosen."""
        return bool(item.flags() & QtCore.Qt.ItemFlag.ItemIsSelectable)

    # Behaviour

    def _select(self, stage_object: Node | NodeComponent | None) -> None:
        """Select an object and show it, if it is listed and can be chosen.

        Args:
            stage_object (Node | NodeComponent | None): object to select.
        """
        item = self._items.get(stage_object.uuid) if stage_object else None
        if item is None or not self._is_selectable(item):
            return
        self.tree.setCurrentItem(item)
        self.tree.scrollToItem(item)

    def _apply_filter(self, text: str) -> None:
        """Show the items matching the search, and what leads to them.

        Args:
            text (str): search text, everything is shown when it is empty.
        """
        text = text.strip().lower()
        root = self.tree.invisibleRootItem()
        for index in range(root.childCount()):
            self._filter_item(root.child(index), text)

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

    def _update_ok_button(self) -> None:
        """Allow OK only when there is something to choose."""
        ok_button = self.buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Ok)
        ok_button.setEnabled(self.selected_object is not None)

    def _on_item_double_clicked(self, item: QtWidgets.QTreeWidgetItem) -> None:
        """Choose the item that was double clicked, if it can be chosen.

        Args:
            item (QtWidgets.QTreeWidgetItem): item.
        """
        if self._is_selectable(item):
            self.accept()
