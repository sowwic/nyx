"""Context menus shared between editor views."""

from PySide6 import QtWidgets

from nyx.editor.core.action_registry import ACTION_REGISTRY
from nyx.editor.core.actions import ActionId


def build_nodes_context_menu(
    parent: QtWidgets.QWidget, has_selection: bool
) -> QtWidgets.QMenu:
    """Build the node context menu used by both the tree and the graph views.

    Args:
        parent: owner of the menu
        has_selection: whether nodes are selected; selection-only entries are
            hidden otherwise
    """
    action = ACTION_REGISTRY.action
    menu = QtWidgets.QMenu("", parent)
    menu.addAction(action(ActionId.CREATE_NODE))
    if has_selection:
        menu.addSeparator()
        menu.addAction(action(ActionId.COPY))
        menu.addAction(action(ActionId.CUT))

    menu.addAction(action(ActionId.PASTE))

    if has_selection:
        menu.addSeparator()
        menu.addAction(action(ActionId.FOCUS_SELECTED))
        menu.addAction(action(ActionId.COPY_NODE_PATH))
        menu.addAction(action(ActionId.DELETE_NODE))
    return menu
