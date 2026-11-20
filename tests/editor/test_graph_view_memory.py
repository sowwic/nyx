import pytest
from PySide6 import QtCore

from nyx.api.v1 import Stage, commands

CENTER_TOLERANCE = 1.0


@pytest.fixture
def editor(main_window, stage_editor, qtbot):
    """The active editor, with its view shown: the view is only recorded then."""
    main_window.show()
    qtbot.waitExposed(main_window)
    qtbot.waitUntil(stage_editor.gr_view.isVisible, timeout=2000)
    return stage_editor


@pytest.fixture
def parent(editor, create_node):
    return create_node(editor.stage, "parent")


@pytest.fixture
def child(editor, create_node, parent):
    return create_node(editor.stage, "child", parent=parent)


def set_view(editor, zoom, center):
    """Move the view and say where it ended up: the scene limits where it can center."""
    editor.gr_view.apply_view_state({"zoom": zoom, "center": list(center)})
    return editor.gr_view.get_view_state()


def assert_view(editor, expected):
    state = editor.gr_view.get_view_state()
    assert state["zoom"] == pytest.approx(expected["zoom"])
    assert state["center"] == pytest.approx(expected["center"], abs=CENTER_TOLERANCE)


def assert_graph_view(node, expected):
    position, zoom = node.get_graph_view()
    assert zoom == pytest.approx(expected["zoom"])
    assert [position.x(), position.y()] == pytest.approx(
        expected["center"], abs=CENTER_TOLERANCE
    )


def test_leaving_a_scope_records_the_view_in_the_metadata_of_its_node(editor, parent):
    root = editor.stage.root_node
    root_view = set_view(editor, 2.0, (120.0, -40.0))

    editor.set_scope_path(parent)

    assert_graph_view(root, root_view)
    assert set(root.metadata) >= {"graph_view_position", "graph_view_zoom"}
    assert parent.get_graph_view() is None


def test_coming_back_to_a_scope_restores_its_view(editor, parent):
    root = editor.stage.root_node
    root_view = set_view(editor, 2.0, (120.0, -40.0))
    editor.set_scope_path(parent)
    parent_view = set_view(editor, 3.0, (10.0, 15.0))

    editor.set_scope_path(root)
    assert_view(editor, root_view)

    editor.set_scope_path(parent)
    assert_view(editor, parent_view)


def test_a_scope_that_was_never_shown_keeps_the_current_view(editor, parent):
    root_view = set_view(editor, 2.0, (120.0, -40.0))

    editor.set_scope_path(parent)

    assert_view(editor, root_view)


def test_each_scope_remembers_its_own_view(editor, parent, child):
    root = editor.stage.root_node
    root_view = set_view(editor, 1.0, (0.0, 0.0))
    editor.set_scope_path(parent)
    parent_view = set_view(editor, 2.0, (50.0, 60.0))
    editor.set_scope_path(child)
    child_view = set_view(editor, 4.0, (-70.0, 80.0))

    editor.set_scope_path(root)

    assert_graph_view(root, root_view)
    assert_graph_view(parent, parent_view)
    assert_graph_view(child, child_view)
    editor.set_scope_path(child)
    assert_view(editor, child_view)


def test_setting_the_scope_that_is_already_shown_does_nothing(editor):
    root = editor.stage.root_node
    root_view = set_view(editor, 2.0, (120.0, -40.0))

    editor.set_scope_path(root)

    assert root.get_graph_view() is None
    assert_view(editor, root_view)


def test_a_silent_scope_change_records_but_does_not_move_the_view(editor, parent):
    root = editor.stage.root_node
    root_view = set_view(editor, 2.0, (120.0, -40.0))
    parent.set_graph_view(QtCore.QPointF(300, 300), 5.0)

    editor.set_scope_path(parent, silent=True)

    assert_graph_view(root, root_view)
    assert_view(editor, root_view)


def test_nothing_is_recorded_while_the_view_is_hidden(editor, parent):
    root = editor.stage.root_node
    set_view(editor, 2.0, (120.0, -40.0))
    editor.gr_view.hide()
    try:
        editor.set_scope_path(parent)
    finally:
        editor.gr_view.show()

    assert root.get_graph_view() is None


def test_a_deleted_scope_is_not_recorded_and_the_parent_view_comes_back(
    editor, parent, child
):
    set_view(editor, 1.0, (0.0, 0.0))
    editor.set_scope_path(parent)
    parent_view = set_view(editor, 2.0, (50.0, 60.0))
    editor.set_scope_path(child)
    set_view(editor, 4.0, (-70.0, 80.0))

    editor.stage.push_command(commands.DeleteNodeCommand(editor.stage, [child]))

    assert editor.get_scope_path() == parent.path
    assert_view(editor, parent_view)


def test_saving_records_the_view_of_the_scope_being_shown(editor, parent, tmp_path):
    editor.set_scope_path(parent)
    parent_view = set_view(editor, 2.0, (50.0, 60.0))
    editor.stage.file_path = tmp_path / "stage.nyx"

    assert editor.on_stage_save()

    loaded = Stage()
    loaded.import_json(tmp_path / "stage.nyx")
    assert_graph_view(loaded.get_object(parent.path), parent_view)


def test_a_saved_stage_opens_with_the_views_it_was_saved_with(editor, parent, tmp_path):
    root_view = set_view(editor, 3.0, (200.0, -100.0))
    editor.set_scope_path(parent)
    parent_view = set_view(editor, 2.0, (50.0, 60.0))
    editor.set_scope_path(editor.stage.root_node)
    editor.stage.file_path = tmp_path / "stage.nyx"
    editor.on_stage_save()
    set_view(editor, 1.0, (0.0, 0.0))

    editor.load_stage_file(tmp_path / "stage.nyx")

    assert_view(editor, root_view)
    editor.set_scope_path("/stage/parent")
    assert_view(editor, parent_view)


def test_a_session_view_still_wins_over_the_recorded_one(editor, parent):
    set_view(editor, 1.0, (0.0, 0.0))
    editor.set_scope_path(parent)
    set_view(editor, 2.0, (50.0, 60.0))
    editor.set_scope_path(editor.stage.root_node)

    editor.apply_session_state(
        {"scope": parent.path.as_posix(), "view": {"zoom": 4.0, "center": [5.0, 5.0]}}
    )

    assert editor.gr_view.get_view_state()["zoom"] == pytest.approx(4.0)


def test_recording_does_not_make_the_stage_modified(editor, parent):
    editor.stage.undo_stack.setClean()
    set_view(editor, 2.0, (120.0, -40.0))

    editor.set_scope_path(parent)

    assert editor.stage.undo_stack.isClean()


@pytest.mark.parametrize("zoom", [1.0, 2.0, 4.0])
def test_applying_a_view_state_again_does_not_move_the_view(editor, zoom):
    state = set_view(editor, zoom, (100.0, -50.0))

    for _ in range(3):
        editor.gr_view.apply_view_state(state)

        assert_view(editor, state)


@pytest.mark.parametrize("zoom", [1.0, 2.0, 4.0])
def test_a_view_state_is_applied_to_within_a_scrollbar_step(editor, zoom):
    set_view(editor, zoom, (100.0, -50.0))

    center = editor.gr_view.get_view_state()["center"]

    # The scrollbars of this scene move in steps of several pixels
    assert abs(center[0] - 100.0) * zoom <= 20.0
    assert abs(center[1] + 50.0) * zoom <= 20.0
