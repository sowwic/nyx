from PySide6 import QtCore, QtGui, QtWidgets

from nyx.api.v1 import CoreNodes
from nyx.core import Node
from nyx.editor.views.node_item_delegate import NodeItemDelegate

HAS_DECORATION = QtWidgets.QStyleOptionViewItem.ViewItemFeature.HasDecoration


def style_option(delegate, node) -> QtWidgets.QStyleOptionViewItem:
    option = QtWidgets.QStyleOptionViewItem()
    delegate.initStyleOption(option, node.index())
    return option


def test_option_gets_icon_from_type_icon_role(stage_editor, create_node):
    node = create_node(stage_editor.stage, "n")
    delegate = NodeItemDelegate()
    option = style_option(delegate, node)

    assert not option.icon.isNull()
    assert option.features & HAS_DECORATION
    expected = QtGui.QIcon(node.data(Node.Roles.TYPE_ICON))
    assert option.icon.pixmap(16, 16).toImage() == expected.pixmap(16, 16).toImage()


def test_different_node_types_get_different_icons(stage_editor, create_node):
    plain = create_node(stage_editor.stage, "plain")
    log = create_node(stage_editor.stage, "log", type_id=CoreNodes.LOG)
    assert plain.data(Node.Roles.TYPE_ICON) != log.data(Node.Roles.TYPE_ICON)

    delegate = NodeItemDelegate()
    plain_option = style_option(delegate, plain)
    log_option = style_option(delegate, log)
    plain_image = plain_option.icon.pixmap(16, 16).toImage()
    log_image = log_option.icon.pixmap(16, 16).toImage()
    assert plain_image != log_image


def test_icons_are_cached_per_path(stage_editor, create_node):
    first = create_node(stage_editor.stage, "a")
    second = create_node(stage_editor.stage, "b")
    delegate = NodeItemDelegate()

    style_option(delegate, first)
    style_option(delegate, second)

    assert list(delegate._icon_cache) == [first.data(Node.Roles.TYPE_ICON)]


def test_missing_or_invalid_icon_role_leaves_option_without_icon(
    stage_editor, create_node
):
    node = create_node(stage_editor.stage, "n")
    delegate = NodeItemDelegate()
    for value in (None, "", "not/an/existing/icon.png", 42):
        node.setData(value, Node.Roles.TYPE_ICON)
        option = style_option(delegate, node)
        assert option.icon.isNull()
        assert not option.features & HAS_DECORATION


def test_tree_view_uses_delegate_and_icon_size(main_window):
    tree = main_window.stage_tree_view
    assert isinstance(tree.itemDelegate(), NodeItemDelegate)
    assert tree.iconSize() == QtCore.QSize(16, 16)


def test_tree_row_renders_icon(main_window, stage_editor, create_node, qtbot):
    node = create_node(stage_editor.stage, "n")
    tree = main_window.stage_tree_view
    tree.resize(300, 200)
    tree.show()
    qtbot.waitExposed(tree)

    with_icon = tree.viewport().grab(tree.visualRect(node.index())).toImage()
    node.setData(None, Node.Roles.TYPE_ICON)
    without_icon = tree.viewport().grab(tree.visualRect(node.index())).toImage()

    assert with_icon != without_icon
