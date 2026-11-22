import pytest
from PySide6 import QtCore

from nyx.api.v1 import CoreNodes, Node
from nyx.editor.widgets.stage_tree_widget import StageTreeWidget


@pytest.fixture(autouse=True)
def clear_search(main_window):
    """The window is shared by the tests, give the next one an empty search bar."""
    yield
    main_window.stage_tree_widget.search_bar.clear()
    main_window.stage_tree_view.set_filter("")


def select(stage_editor, *nodes):
    stage_editor.selection_model.clearSelection()
    for node in nodes:
        stage_editor.selection_model.select(
            node.index(), QtCore.QItemSelectionModel.SelectionFlag.Select
        )


def listed_names(tree):
    root = tree.rootIndex()
    model = tree.model()
    return [
        model.index(row, 0, root).data(Node.Roles.NAME)
        for row in range(model.rowCount(root))
    ]


def search(widget, text, qtbot):
    """Type in the QML search bar."""
    field = widget.search_bar.rootObject().findChild(QtCore.QObject, "searchField")
    field.setProperty("text", text)
    # A token being typed is not the text of the search yet, wait for the field
    qtbot.waitUntil(lambda: field.property("text") == text, timeout=1000)


def test_tree_panel_content_is_the_widget_with_the_view_under_the_search_bar(
    main_window,
):
    widget = main_window.stage_tree_widget
    assert isinstance(widget, StageTreeWidget)
    assert main_window.stage_tree_view is widget.tree_view
    assert widget.main_layout.itemAt(0).widget() is widget.search_bar
    assert widget.main_layout.itemAt(1).widget() is widget.tree_view


def test_typing_in_the_search_bar_filters_the_tree(
    main_window, stage_editor, create_node, qtbot
):
    create_node(stage_editor.stage, "alpha")
    create_node(stage_editor.stage, "beta")
    widget = main_window.stage_tree_widget

    search(widget, "alp", qtbot)

    assert listed_names(widget.tree_view) == ["alpha"]


def test_clearing_the_search_bar_lists_every_node_again(
    main_window, stage_editor, create_node, qtbot
):
    create_node(stage_editor.stage, "alpha")
    create_node(stage_editor.stage, "beta")
    widget = main_window.stage_tree_widget
    search(widget, "alp", qtbot)

    widget.search_bar.clear()

    qtbot.waitUntil(lambda: widget.search_bar.text == "", timeout=1000)
    assert listed_names(widget.tree_view) == ["alpha", "beta"]


def test_a_token_typed_in_the_search_bar_filters_the_tree(
    main_window, stage_editor, create_node, qtbot
):
    create_node(stage_editor.stage, "plain")
    create_node(stage_editor.stage, "loop", type_id=CoreNodes.FOR_LOOP)
    widget = main_window.stage_tree_widget

    search(widget, "tag:logic", qtbot)

    assert listed_names(widget.tree_view) == ["loop"]


def test_a_token_made_into_a_chip_keeps_filtering(
    main_window, stage_editor, create_node, qtbot
):
    create_node(stage_editor.stage, "plain")
    create_node(stage_editor.stage, "loop", type_id=CoreNodes.FOR_LOOP)
    widget = main_window.stage_tree_widget
    search(widget, "tag:logic", qtbot)

    QtCore.QMetaObject.invokeMethod(widget.search_bar.rootObject(), "commitToken")

    qtbot.waitUntil(lambda: widget.search_bar.tokens == ["tag:logic"], timeout=1000)
    assert widget.search_bar.text == ""
    assert listed_names(widget.tree_view) == ["loop"]


def test_matches_are_expanded(main_window, stage_editor, create_node, qtbot):
    parent = create_node(stage_editor.stage, "parent")
    create_node(stage_editor.stage, "needle", parent=parent)
    widget = main_window.stage_tree_widget

    search(widget, "needle", qtbot)

    assert widget.tree_view.isExpanded(widget.tree_view.index_of(parent))


def test_selecting_in_the_tree_selects_in_the_graph(
    main_window, stage_editor, create_node
):
    a = create_node(stage_editor.stage, "a")
    create_node(stage_editor.stage, "b")
    tree = main_window.stage_tree_view

    tree.selectionModel().select(
        tree.index_of(a), QtCore.QItemSelectionModel.SelectionFlag.ClearAndSelect
    )

    assert stage_editor.list_selected_objects() == [a]


def test_selecting_in_the_graph_selects_in_the_tree(
    main_window, stage_editor, create_node
):
    a = create_node(stage_editor.stage, "a")
    tree = main_window.stage_tree_view

    select(stage_editor, a)

    assert tree.selectionModel().selectedIndexes() == [tree.index_of(a)]


def test_filtering_out_a_selected_node_keeps_it_selected_in_the_graph(
    main_window, stage_editor, create_node, qtbot
):
    a = create_node(stage_editor.stage, "alpha")
    create_node(stage_editor.stage, "beta")
    select(stage_editor, a)
    widget = main_window.stage_tree_widget

    search(widget, "beta", qtbot)

    assert stage_editor.list_selected_objects() == [a]
    assert not widget.tree_view.selectionModel().hasSelection()
    assert not widget.tree_view.selected_nodes()


def test_a_selected_node_is_selected_in_the_tree_when_the_filter_shows_it_again(
    main_window, stage_editor, create_node, qtbot
):
    a = create_node(stage_editor.stage, "alpha")
    create_node(stage_editor.stage, "beta")
    select(stage_editor, a)
    widget = main_window.stage_tree_widget
    search(widget, "beta", qtbot)

    widget.search_bar.clear()

    qtbot.waitUntil(lambda: widget.search_bar.text == "", timeout=1000)
    assert list(widget.tree_view.selected_nodes()) == [a]
    assert widget.tree_view.selectionModel().isSelected(widget.tree_view.index_of(a))


def test_selecting_in_a_filtered_tree_replaces_the_selection_of_the_graph(
    main_window, stage_editor, create_node, qtbot
):
    a = create_node(stage_editor.stage, "alpha")
    b = create_node(stage_editor.stage, "beta")
    select(stage_editor, a)
    widget = main_window.stage_tree_widget
    search(widget, "beta", qtbot)
    tree = widget.tree_view

    tree.selectionModel().select(
        tree.index_of(b), QtCore.QItemSelectionModel.SelectionFlag.ClearAndSelect
    )

    assert stage_editor.list_selected_objects() == [b]


def test_deleting_with_a_filter_deletes_only_the_listed_nodes(
    main_window, stage_editor, create_node, qtbot
):
    a = create_node(stage_editor.stage, "alpha")
    b = create_node(stage_editor.stage, "beta")
    select(stage_editor, a, b)
    widget = main_window.stage_tree_widget
    search(widget, "beta", qtbot)

    widget.tree_view.delete_selected_node()

    remaining = [
        n.name for n in stage_editor.stage.list_children(stage_editor.stage.root_node)
    ]
    assert remaining == ["alpha"]


def test_double_clicking_a_filtered_row_emits_its_node(
    main_window, stage_editor, create_node, qtbot
):
    create_node(stage_editor.stage, "alpha")
    b = create_node(stage_editor.stage, "beta")
    widget = main_window.stage_tree_widget
    search(widget, "beta", qtbot)
    tree = widget.tree_view

    with qtbot.waitSignal(tree.node_doubleclicked, timeout=1000) as blocker:
        tree.doubleClicked.emit(tree.index_of(b))

    assert blocker.args == [b]


def test_the_filter_survives_switching_stage(
    main_window, stage_editor, create_node, qtbot
):
    create_node(stage_editor.stage, "alpha")
    widget = main_window.stage_tree_widget
    search(widget, "alp", qtbot)

    main_window.stage_tree_view.set_stage(None)
    main_window.stage_tree_view.set_stage(stage_editor.stage)

    assert listed_names(widget.tree_view) == ["alpha"]
    assert widget.tree_view.filter_model.text == "alp"
