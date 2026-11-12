"""Context menus shared between editor views."""

from PySide6 import QtCore, QtWidgets

from nyx.editor.core.action_registry import ACTION_REGISTRY
from nyx.editor.core.actions import ActionId
from nyx.editor.graphics.graphics_util_object import GraphicsUtilObject


def show_menu(menu: QtWidgets.QMenu, global_pos: QtCore.QPoint) -> None:
    """Show a menu at a position and wait until it is closed.

    Args:
        menu (QtWidgets.QMenu): menu to show.
        global_pos (QtCore.QPoint): position in screen coordinates.
    """
    menu.exec(global_pos)


def build_nodes_context_menu(
    parent: QtWidgets.QWidget,
    has_selection: bool,
    has_reference: bool = False,
    with_util_objects: bool = False,
) -> QtWidgets.QMenu:
    """Build the node context menu used by both the tree and the graph views.

    Args:
        parent: owner of the menu
        has_selection: whether nodes are selected; selection-only entries are
            hidden otherwise
        has_reference: whether a selected node is loaded from a stage file; the
            entries for those are hidden otherwise
        with_util_objects: whether to offer creating notes and groups, which only
            the graph can show
    """
    action = ACTION_REGISTRY.action
    menu = QtWidgets.QMenu("", parent)
    menu.addAction(action(ActionId.CREATE_NODE))
    if with_util_objects:
        menu.addAction(action(ActionId.CREATE_NOTE))
        menu.addAction(action(ActionId.CREATE_GROUP))
    if has_selection:
        menu.addSeparator()
        menu.addAction(action(ActionId.COPY))
        menu.addAction(action(ActionId.CUT))

    menu.addAction(action(ActionId.PASTE))

    if has_selection:
        menu.addSeparator()
        menu.addAction(action(ActionId.FOCUS_SELECTED))
        menu.addAction(action(ActionId.COPY_NODE_PATH))
        if has_reference:
            menu.addAction(action(ActionId.RELOAD_REFERENCE))
            menu.addAction(action(ActionId.OPEN_REFERENCED_STAGE))
        menu.addAction(action(ActionId.DELETE_NODE))
    return menu


def build_util_object_context_menu(
    parent: QtWidgets.QWidget, gr_util: GraphicsUtilObject
) -> QtWidgets.QMenu:
    """Build the context menu of a note, group or other util object.

    Args:
        parent: owner of the menu
        gr_util: item of the util object under the cursor
    """
    menu = QtWidgets.QMenu("", parent)
    if gr_util.is_editable:
        menu.addAction("Edit...", gr_util.edit)
        color_menu = menu.addMenu("Color")
        for name, color in gr_util.COLOR_PRESETS.items():
            color_menu.addAction(name, lambda color=color: gr_util.set_color(color))
        menu.addSeparator()
        menu.addAction(ACTION_REGISTRY.action(ActionId.DELETE))
    return menu
