import pytest
from nyx.editor.panels.panel_definitions import PanelId
from nyx.editor.views.stage_tree_view import BranchLines, StageTreeView


@pytest.fixture
def tree(main_window, stage_editor):
    yield main_window.stage_tree_view
    # The window is shared by the tests, give the next one an unfiltered tree
    main_window.stage_tree_view.set_filter("")


@pytest.fixture
def nested(stage_editor, create_node):
    """alpha, beta (one, two (two_x, two_y), three), gamma."""
    stage = stage_editor.stage
    nodes = {"alpha": create_node(stage, "alpha")}
    nodes["beta"] = create_node(stage, "beta")
    nodes["one"] = create_node(stage, "one", parent=nodes["beta"])
    nodes["two"] = create_node(stage, "two", parent=nodes["beta"])
    nodes["x"] = create_node(stage, "two_x", parent=nodes["two"])
    nodes["y"] = create_node(stage, "two_y", parent=nodes["two"])
    nodes["three"] = create_node(stage, "three", parent=nodes["beta"])
    nodes["gamma"] = create_node(stage, "gamma")
    return nodes


def lines_of(tree, node) -> BranchLines:
    return tree.get_branch_lines(tree.index_of(node))


def test_top_level_rows_have_no_lines(tree, nested):
    lines = lines_of(tree, nested["beta"])

    assert lines.depth == 0
    assert lines.own_level is None
    assert lines.passing_levels == ()
    assert lines.has_children


def test_a_child_with_a_next_sibling_has_a_full_trunk(tree, nested):
    lines = lines_of(tree, nested["one"])

    assert lines.depth == 1
    assert lines.own_level == 0
    assert lines.has_next_sibling
    assert not lines.has_children


def test_the_last_child_ends_its_trunk(tree, nested):
    lines = lines_of(tree, nested["three"])

    assert lines.own_level == 0
    assert not lines.has_next_sibling


def test_a_grandchild_passes_the_line_of_a_parent_with_a_next_sibling(tree, nested):
    # `two` has `three` after it, so the trunk of beta's children goes on past x and y
    x, y = lines_of(tree, nested["x"]), lines_of(tree, nested["y"])

    assert x.depth == y.depth == 2
    assert x.own_level == y.own_level == 1
    assert x.passing_levels == y.passing_levels == (0,)
    assert x.has_next_sibling and not y.has_next_sibling


def test_a_grandchild_of_the_last_child_passes_no_line(
    tree, nested, create_node, stage_editor
):
    deep = create_node(stage_editor.stage, "deep", parent=nested["three"])

    lines = lines_of(tree, deep)

    assert lines.depth == 2
    assert lines.passing_levels == ()


def test_lines_follow_the_rows_the_filter_lists(tree, nested):
    tree.set_filter("two")

    # Of the children of beta only `two` is listed, so it is the last one, and the
    # filter keeps the children that match too
    assert not lines_of(tree, nested["two"]).has_next_sibling
    assert lines_of(tree, nested["two"]).passing_levels == ()
    assert lines_of(tree, nested["x"]).has_next_sibling


def test_the_lines_are_drawn_with_the_palette(main_window, manager, qtbot, tree, nested):
    main_window.show()
    manager.set_open(PanelId.TREE, True)
    qtbot.waitExposed(main_window)
    tree.expandAll()
    qtbot.wait(100)
    image = tree.viewport().grab().toImage()
    line = tree.palette().color(StageTreeView.BRANCH_LINE_ROLE).rgb()
    trunk_x = tree.indentation() // 2

    def drawn(y: int) -> bool:
        """Check if the pixel of the trunk column at a height has the line color."""
        return image.pixelColor(trunk_x, y).rgb() == line

    first = tree.visualRect(tree.index_of(nested["one"]))
    last = tree.visualRect(tree.index_of(nested["three"]))
    top_level = tree.visualRect(tree.index_of(nested["alpha"]))

    # Full trunk down a row that has a sibling after it
    assert drawn(first.top()) and drawn(first.bottom())
    # The last child's trunk stops at the middle of its row
    assert drawn(last.top()) and drawn(last.center().y())
    assert not drawn(last.bottom())
    # Nothing at the top level
    assert not drawn(top_level.center().y())
