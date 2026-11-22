"""Context menus shared between editor views."""

from PySide6 import QtCore, QtGui, QtWidgets

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


CREATE_MENU_OBJECT_NAME = "create_menu"
SELECT_MENU_OBJECT_NAME = "select_menu"


def add_select_menu(
    menu: QtWidgets.QMenu,
    select_actions: list[QtGui.QAction] | None,
    with_separator: bool = False,
) -> None:
    """Add the Select menu at the end of a menu.

    Args:
        menu (QtWidgets.QMenu): menu to add to.
        select_actions (list[QtGui.QAction] | None): one entry for each of the items
            stacked under the cursor. Nothing is added without any.
        with_separator (bool): add a separator after the menu.
    """
    if not select_actions:
        return
    select_menu = menu.addMenu("Select")
    select_menu.menuAction().setObjectName(SELECT_MENU_OBJECT_NAME)
    select_menu.addActions(select_actions)
    if with_separator:
        menu.addSeparator()


def make_proxy_action(
    parent: QtWidgets.QWidget,
    source: QtGui.QAction,
    text: str,
    icon: QtGui.QIcon | None = None,
) -> QtGui.QAction:
    """Make a menu entry that runs a registered action, under a name of its own.

    The registered actions read "Create note", which is redundant in the Create menu.
    The entry shows the shortcut of the source, which keeps the shortcut itself, and
    copies its enabled state when it is made.

    Args:
        parent (QtWidgets.QWidget): owner of the entry.
        source (QtGui.QAction): action the entry triggers.
        text (str): text of the entry.
        icon (QtGui.QIcon | None): icon of the entry, the one of the source if omitted.

    Returns:
        QtGui.QAction: entry. It has the object name of the source.
    """
    shortcut = source.shortcut().toString(QtGui.QKeySequence.SequenceFormat.NativeText)
    # Text after a tab is the shortcut shown at the right of the entry
    entry = QtGui.QAction(source.icon() if icon is None else icon, text, parent)
    if shortcut:
        entry.setText(f"{text}\t{shortcut}")
    entry.setObjectName(source.objectName())
    entry.setEnabled(source.isEnabled())
    entry.triggered.connect(lambda _checked=False: source.trigger())
    return entry


def build_create_menu(
    parent: QtWidgets.QWidget, spawner_actions: list[QtGui.QAction]
) -> QtWidgets.QMenu:
    """Build the Create menu: a node, then what spawners add.

    Args:
        parent (QtWidgets.QWidget): owner of the menu.
        spawner_actions (list[QtGui.QAction]): entries of the spawners.

    Returns:
        QtWidgets.QMenu: menu.
    """
    menu = QtWidgets.QMenu("Create", parent)
    menu.menuAction().setObjectName(CREATE_MENU_OBJECT_NAME)
    menu.addAction(
        make_proxy_action(menu, ACTION_REGISTRY.action(ActionId.CREATE_NODE), "Node...")
    )
    if spawner_actions:
        menu.addSeparator()
        menu.addActions(spawner_actions)
    return menu


def build_nodes_context_menu(
    parent: QtWidgets.QWidget,
    has_selection: bool,
    has_reference: bool = False,
    spawner_actions: list[QtGui.QAction] | None = None,
    select_actions: list[QtGui.QAction] | None = None,
) -> QtWidgets.QMenu:
    """Build the node context menu used by both the tree and the graph views.

    Args:
        parent: owner of the menu
        has_selection: whether nodes are selected; selection-only entries are
            hidden otherwise
        has_reference: whether a selected node is loaded from a stage file; the
            entries for those are hidden otherwise
        spawner_actions: entries of the spawners, which only the graph can run. They
            go in a Create menu with the node. Without them the menu has an entry
            that creates a node.
        select_actions: entries that select one of the items stacked under the cursor.
            They go in a Select menu below the Create entry.
    """
    action = ACTION_REGISTRY.action
    menu = QtWidgets.QMenu("", parent)
    if spawner_actions is None:
        menu.addAction(action(ActionId.CREATE_NODE))
    else:
        menu.addMenu(build_create_menu(menu, spawner_actions))
    add_select_menu(menu, select_actions)
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
    parent: QtWidgets.QWidget,
    gr_util: GraphicsUtilObject,
    select_actions: list[QtGui.QAction] | None = None,
) -> QtWidgets.QMenu:
    """Build the context menu of a note, group or other util object.

    Args:
        parent: owner of the menu
        gr_util: item of the util object under the cursor
        select_actions: entries that select one of the items stacked under the cursor.
            They go in a Select menu at the top.
    """
    menu = QtWidgets.QMenu("", parent)
    add_select_menu(menu, select_actions, with_separator=True)
    if gr_util.is_editable:
        menu.addAction("Edit...", gr_util.edit)
        color_menu = menu.addMenu("Color")
        for name, color in gr_util.COLOR_PRESETS.items():
            color_menu.addAction(name, lambda color=color: gr_util.set_color(color))
        menu.addSeparator()
        menu.addAction(ACTION_REGISTRY.action(ActionId.DELETE))
    return menu
