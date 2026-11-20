import pytest
from PySide6 import QtCore, QtTest

from nyx.api.v1 import CoreUtilObjects, commands
from nyx.editor.graphics.graphics_node import GraphicsNode
from nyx.editor.utils import context_menus
from nyx.stdlib.graphics_objects.group import GraphicsGroup
from nyx.stdlib.graphics_objects.note import GraphicsNote


@pytest.fixture
def editor(main_window, stage_editor, qtbot):
    main_window.show()
    qtbot.waitExposed(main_window)
    qtbot.waitUntil(stage_editor.gr_view.isVisible, timeout=2000)
    return stage_editor


@pytest.fixture
def make_util(editor):
    def make(type_id, x, y, width, height, **properties):
        command = commands.CreateUtilObjectCommand(
            editor.stage,
            type_id,
            node=None,
            position=(x, y),
            size=(width, height),
            properties=properties or None,
        )
        editor.stage.push_command(command)
        return editor.gr_stage.get_gr_util_object(command.result_object)

    return make


@pytest.fixture
def group(make_util):
    def make(x, y, width, height, title="group"):
        return make_util(CoreUtilObjects.GROUP, x, y, width, height, title=title)

    return make


@pytest.fixture
def note(make_util):
    def make(x, y, text=""):
        return make_util(CoreUtilObjects.NOTE, x, y, 200, 100, text=text)

    return make


def view_point(editor, x, y):
    return editor.gr_view.mapFromScene(QtCore.QPointF(x, y))


def click(editor, x, y):
    QtTest.QTest.mouseClick(
        editor.gr_view.viewport(),
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
        view_point(editor, x, y),
    )


def titles(items):
    return [item.util_object.title for item in items]


# ---- Smaller groups are above larger ones ----
@pytest.mark.parametrize("inner_first", [True, False])
def test_a_group_inside_another_is_above_it_whichever_was_created_first(
    editor, group, inner_first
):
    if inner_first:
        inner = group(100, 100, 200, 150, "inner")
        outer = group(0, 0, 600, 400, "outer")
    else:
        outer = group(0, 0, 600, 400, "outer")
        inner = group(100, 100, 200, 150, "inner")

    stacked = editor.gr_view.list_stacked_items(view_point(editor, 150, 180))

    assert inner.zValue() > outer.zValue()
    assert stacked == [inner, outer]


def test_the_title_and_body_of_an_inner_group_can_be_clicked(editor, group):
    inner = group(100, 100, 200, 150, "inner")
    outer = group(0, 0, 600, 400, "outer")

    click(editor, 150, 110)  # the title of the inner group
    assert inner.isSelected() and not outer.isSelected()

    editor.gr_stage.clearSelection()
    click(editor, 150, 200)  # its body
    assert inner.isSelected() and not outer.isSelected()

    editor.gr_stage.clearSelection()
    click(editor, 500, 300)  # the outer group outside of the inner one
    assert outer.isSelected() and not inner.isSelected()


def test_three_nested_groups_stack_from_the_smallest_up(editor, group):
    outer = group(0, 0, 900, 600, "outer")
    middle = group(100, 100, 500, 300, "middle")
    inner = group(150, 150, 200, 100, "inner")
    outer_again = group(1000, 0, 100, 100, "elsewhere")

    stacked = editor.gr_view.list_stacked_items(view_point(editor, 200, 200))

    assert stacked == [inner, middle, outer]
    assert outer_again not in stacked


def test_resizing_a_group_stacks_it_again(editor, group):
    inner = group(100, 100, 200, 150, "inner")
    outer = group(0, 0, 600, 400, "outer")
    assert inner.zValue() > outer.zValue()

    editor.stage.push_command(
        commands.SetUtilObjectPropertiesCommand(
            editor.stage, {inner.util_object: {"size": [800.0, 700.0]}}
        )
    )

    inner = editor.gr_stage.get_gr_util_object(inner.util_object)
    outer = editor.gr_stage.get_gr_util_object(outer.util_object)
    assert outer.zValue() > inner.zValue()


def test_groups_of_the_same_size_keep_the_order_they_were_created_in(editor, group):
    first = group(0, 0, 300, 200, "first")
    second = group(0, 0, 300, 200, "second")

    assert first.zValue() == second.zValue()
    stacked = editor.gr_view.list_stacked_items(view_point(editor, 100, 100))
    assert stacked == [second, first]


def test_groups_stay_below_the_links_nodes_and_notes(editor, group):
    tiny = group(0, 0, 80, 60, "tiny")
    huge = group(0, 0, 50_000, 50_000, "huge")

    assert tiny.zValue() < -1.0  # links are at -1
    assert huge.zValue() >= GraphicsGroup.Z_VALUE
    assert tiny.zValue() < 0.0 < GraphicsNote.Z_VALUE


# ---- The items stacked under a point ----
def test_a_node_above_a_group_is_listed_first_and_once(editor, group, create_node):
    framing = group(-200, -200, 800, 600, "framing")
    node = create_node(editor.stage, "a")
    editor.gr_stage.rebuild_current_scope()
    gr_node = editor.gr_stage.get_gr_node(node)
    center = gr_node.pos() + QtCore.QPointF(gr_node.width / 2, gr_node.height / 2)

    stacked = editor.gr_view.list_stacked_items(
        view_point(editor, center.x(), center.y())
    )

    assert stacked == [gr_node, framing]
    assert isinstance(stacked[0], GraphicsNode)


def test_the_list_is_limited(editor, note):
    for _ in range(editor.gr_view.MAX_STACKED_ITEMS + 5):
        note(0, 0)

    stacked = editor.gr_view.list_stacked_items(view_point(editor, 50, 50))

    assert len(stacked) == editor.gr_view.MAX_STACKED_ITEMS


def test_nothing_is_listed_where_there_is_nothing(editor):
    assert editor.gr_view.list_stacked_items(view_point(editor, 5000, 5000)) == []


# ---- Labels ----
def test_labels_tell_the_items_apart(editor, group, note):
    assert group(0, 0, 100, 100, "Patch env").get_select_label() == "Group: Patch env"
    assert group(0, 0, 100, 100, "  ").get_select_label() == "Group"
    assert note(0, 0, "").get_select_label() == "Note"
    assert note(0, 0, "\n  first line\nsecond").get_select_label() == "Note: first line"


def test_a_long_note_text_is_cut_in_the_label(editor, note):
    label = note(0, 0, "x" * 100).get_select_label()

    assert label == "Note: " + "x" * (GraphicsNote.SELECT_LABEL_LENGTH - 1) + "…"


# ---- The Select menu ----
def test_there_is_nothing_to_choose_from_with_one_item(editor, group):
    group(0, 0, 300, 200, "alone")

    actions = editor.gr_view.build_select_actions(
        editor.gr_view, view_point(editor, 100, 100)
    )

    assert actions == []


def test_the_select_entries_list_the_items_topmost_first(
    editor, group, note, create_node
):
    group(0, 0, 600, 400, "outer")
    group(100, 100, 300, 200, "inner")
    note(150, 150, "a sticky")

    actions = editor.gr_view.build_select_actions(
        editor.gr_view, view_point(editor, 200, 200)
    )

    assert [action.text() for action in actions] == [
        "Note: a sticky",
        "Group: inner",
        "Group: outer",
    ]
    assert all(not action.icon().isNull() for action in actions)


def test_choosing_an_entry_selects_only_that_item(editor, group):
    first = group(700, 0, 300, 200, "twin a")
    second = group(700, 0, 300, 200, "twin b")
    # The second one is on top, a click can't get to the first
    click(editor, 750, 100)
    assert second.isSelected() and not first.isSelected()
    actions = editor.gr_view.build_select_actions(
        editor.gr_view, view_point(editor, 750, 100)
    )
    assert [action.text() for action in actions] == ["Group: twin b", "Group: twin a"]

    actions[1].trigger()

    assert first.isSelected() and not second.isSelected()
    assert editor.list_selected_objects() == [first.util_object]


def test_choosing_a_node_selects_the_node(editor, group, create_node):
    group(-200, -200, 800, 600, "framing")
    node = create_node(editor.stage, "a")
    editor.gr_stage.rebuild_current_scope()
    gr_node = editor.gr_stage.get_gr_node(node)
    center = gr_node.pos() + QtCore.QPointF(gr_node.width / 2, gr_node.height / 2)
    point = view_point(editor, center.x(), center.y())
    editor.gr_stage.clearSelection()

    actions = editor.gr_view.build_select_actions(editor.gr_view, point)
    labels = [action.text() for action in actions]
    actions[labels.index(node.display_name)].trigger()

    assert editor.list_selected_nodes() == [node]


def capture_context_menu(editor, monkeypatch, x, y):
    menus = []
    monkeypatch.setattr(
        context_menus, "show_menu", lambda menu, global_pos: menus.append(menu)
    )
    editor.gr_view.show_context_menu(view_point(editor, x, y))
    return menus[0]


def select_menu_of(menu):
    found = [
        action
        for action in menu.actions()
        if action.objectName() == context_menus.SELECT_MENU_OBJECT_NAME
    ]
    return found[0].menu() if found else None


def test_the_context_menu_of_a_group_has_a_select_menu_when_items_are_stacked(
    editor, group, monkeypatch
):
    group(0, 0, 600, 400, "outer")
    group(100, 100, 300, 200, "inner")

    menu = capture_context_menu(editor, monkeypatch, 200, 200)

    select_menu = select_menu_of(menu)
    assert [a.text() for a in select_menu.actions()] == ["Group: inner", "Group: outer"]
    assert menu.actions()[0].menu() is select_menu
    assert menu.actions()[1].isSeparator()
    assert any(action.text() == "Edit..." for action in menu.actions())


def test_the_context_menu_of_a_single_group_has_no_select_menu(
    editor, group, monkeypatch
):
    group(0, 0, 300, 200, "alone")

    menu = capture_context_menu(editor, monkeypatch, 100, 100)

    assert select_menu_of(menu) is None
    assert any(action.text() == "Edit..." for action in menu.actions())


def test_the_menu_of_a_node_over_a_group_has_a_select_menu(
    editor, group, create_node, monkeypatch
):
    group(-200, -200, 800, 600, "framing")
    node = create_node(editor.stage, "a")
    editor.gr_stage.rebuild_current_scope()
    gr_node = editor.gr_stage.get_gr_node(node)
    center = gr_node.pos() + QtCore.QPointF(gr_node.width / 2, gr_node.height / 2)

    menu = capture_context_menu(editor, monkeypatch, center.x(), center.y())

    select_menu = select_menu_of(menu)
    assert [a.text() for a in select_menu.actions()] == [
        node.display_name,
        "Group: framing",
    ]
    names = [action.objectName() for action in menu.actions()]
    # Select comes right below Create
    assert names[:2] == [
        context_menus.CREATE_MENU_OBJECT_NAME,
        context_menus.SELECT_MENU_OBJECT_NAME,
    ]


def test_the_select_menu_is_below_the_create_menu_with_a_selection(
    editor, group, create_node, monkeypatch
):
    group(-200, -200, 800, 600, "framing")
    node = create_node(editor.stage, "a")
    editor.gr_stage.rebuild_current_scope()
    gr_node = editor.gr_stage.get_gr_node(node)
    gr_node.setSelected(True)
    center = gr_node.pos() + QtCore.QPointF(gr_node.width / 2, gr_node.height / 2)

    menu = capture_context_menu(editor, monkeypatch, center.x(), center.y())

    layout = [
        "-" if action.isSeparator() else action.objectName() for action in menu.actions()
    ]
    assert layout[:3] == [
        context_menus.CREATE_MENU_OBJECT_NAME,
        context_menus.SELECT_MENU_OBJECT_NAME,
        "-",
    ]
    assert layout[3] != "-"  # one separator, not two


def test_the_empty_space_menu_has_no_select_menu(editor, monkeypatch):
    menu = capture_context_menu(editor, monkeypatch, 5000, 5000)

    assert select_menu_of(menu) is None
    assert context_menus.CREATE_MENU_OBJECT_NAME in [
        action.objectName() for action in menu.actions()
    ]
