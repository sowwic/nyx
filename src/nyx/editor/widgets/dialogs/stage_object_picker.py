from __future__ import annotations

import typing

from PySide6 import QtWidgets

from nyx.core.node import Node
from nyx.core.node_component import NodeComponent
from nyx.editor.widgets.stage_object_tree_widget import StageObjectTreeWidget
from nyx.utils import pyside_fn

if typing.TYPE_CHECKING:
    from nyx.core.stage import Stage


class StageObjectPickerDialog(QtWidgets.QDialog):
    """Dialog to choose a node or a component from a searchable tree of the stage.

    Nodes are listed with their components below them. What the caller can't use is
    shown but can't be chosen, see `target_types`.
    """

    def __init__(
        self,
        stage: Stage,
        target_types: tuple[type, ...] = (Node, NodeComponent),
        current_target: Node | NodeComponent | None = None,
        excluded: typing.Iterable[Node | NodeComponent] = (),
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        """Initialize StageObjectPickerDialog.

        Args:
            stage (Stage): stage to choose from.
            target_types (tuple[type, ...]): what can be chosen, `Node` and
                `NodeComponent`. Components are not listed when it has no
                `NodeComponent`.
            current_target (Node | NodeComponent | None): object to start at.
            excluded (typing.Iterable[Node | NodeComponent]): objects that are shown
                but can't be chosen.
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("Select stage object")
        self.resize(640, 480)

        self.search_field = QtWidgets.QLineEdit(self)
        self.search_field.setPlaceholderText("Search")
        self.search_field.setClearButtonEnabled(True)
        pyside_fn.add_search_icon(self.search_field)
        self.tree = StageObjectTreeWidget(stage, target_types, excluded, self)
        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel,
            self,
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.search_field)
        layout.addWidget(self.tree)
        layout.addWidget(self.buttons)

        self.search_field.textChanged.connect(self.tree.filter_by_text)
        self.tree.itemSelectionChanged.connect(self._update_ok_button)
        self.tree.object_activated.connect(self.accept)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        self.tree.select_object(current_target)
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
            excluded=cls._components_of_the_node(component),
            parent=parent,
        )
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            return dialog.selected_object
        return None

    @staticmethod
    def _components_of_the_node(component: NodeComponent) -> list[NodeComponent]:
        """Get the components of the node a component belongs to.

        Args:
            component (NodeComponent): component.

        Returns:
            list[NodeComponent]: its siblings and itself, empty if it has no node.
        """
        node = getattr(component, "node", None)
        return node.components_model.list_components() if node is not None else []

    @property
    def selected_object(self) -> Node | NodeComponent | None:
        """Node | NodeComponent | None: the chosen object, None if there is none."""
        return self.tree.selected_object

    def _update_ok_button(self) -> None:
        """Allow OK only when there is something to choose."""
        ok_button = self.buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Ok)
        ok_button.setEnabled(self.selected_object is not None)
