import logging

import pytest
from PySide6 import QtCore, QtGui, QtWidgets

from nyx.api.v1 import CoreSpawners, CoreNodes, CoreUtilObjects, NYX_REGISTRY, commands
from nyx.api.v1.editor_utils import SpawnContext, StageObjectSpawner, UtilObjectSpawner
from nyx.core.exceptions import NyxCommandValidationError
from nyx.editor.core.action_registry import ACTION_REGISTRY
from nyx.editor.core.actions import ActionId
from nyx.editor.utils import context_menus
from nyx.stdlib.spawners.group import GroupSpawner
from nyx.stdlib.spawners.note import NoteSpawner
from nyx.stdlib.util_objects.note import NoteObject


class StickySpawner(UtilObjectSpawner):
    """Creates a note with text, a little away from the click."""

    @classmethod
    def get_type_id(cls) -> str:
        return "test.create_sticky"

    @classmethod
    def get_util_object_type_id(cls) -> str:
        return CoreUtilObjects.NOTE

    @classmethod
    def get_display_name(cls) -> str:
        return "Sticky"

    @classmethod
    def get_description(cls) -> str:
        return "A note with text."

    @classmethod
    def get_creation_geometry(cls, context):
        return context.position + QtCore.QPointF(10, 10), QtCore.QSizeF(100, 80)

    @classmethod
    def get_creation_properties(cls, context):
        return {"text": "hello"}


class UnknownTypeSpawner(UtilObjectSpawner):
    @classmethod
    def get_type_id(cls) -> str:
        return "test.create_unknown"

    @classmethod
    def get_util_object_type_id(cls) -> str:
        return "test:unknown"


class ActionNodeSpawner(StageObjectSpawner):
    """Creates a node, which is not a util object."""

    @classmethod
    def get_type_id(cls) -> str:
        return "test.create_action_node"

    @classmethod
    def get_display_name(cls) -> str:
        return "Action node"

    def spawn(self, context):
        command = commands.CreateNodeCommand(
            stage=context.stage,
            type_id=CoreNodes.ACTION,
            parent_node=context.scope_node,
            position=context.position,
        )
        return self._spawn(context.stage, command, lambda: command.result_node)


class FailingSpawner(StageObjectSpawner):
    @classmethod
    def get_type_id(cls) -> str:
        return "test.create_failing"

    @classmethod
    def get_display_name(cls) -> str:
        return "Failing"

    def spawn(self, context):
        raise NyxCommandValidationError("no way")


@pytest.fixture
def register_spawners():
    registered = []

    def register(*spawner_classes):
        for spawner_cls in spawner_classes:
            NYX_REGISTRY.spawners[spawner_cls.get_type_id()] = spawner_cls
            registered.append(spawner_cls.get_type_id())

    yield register
    for type_id in registered:
        NYX_REGISTRY.spawners.pop(type_id, None)


@pytest.fixture
def actions(stage_editor):
    return stage_editor.gr_view.edit_actions


def select_nodes(stage_editor, *nodes):
    stage_editor.select_nodes(list(nodes))


def util_objects(stage_editor):
    return [gr.util_object for gr in stage_editor.gr_stage.gr_util_objects()]


def test_the_stdlib_registers_the_note_and_group_spawners_first():
    assert list(NYX_REGISTRY.spawners)[:2] == [CoreSpawners.NOTE, CoreSpawners.GROUP]
    assert NYX_REGISTRY.get_spawner_cls(CoreSpawners.NOTE) is NoteSpawner
    assert NYX_REGISTRY.get_spawner_cls(CoreSpawners.GROUP) is GroupSpawner


def test_a_util_object_spawner_takes_its_texts_from_the_util_object_type():
    assert NoteSpawner.get_display_name() == "Note"
    assert NoteSpawner.get_icon() == NoteObject.get_type_icon()
    assert NoteSpawner.get_description() == NoteObject.get_description()


def test_a_util_object_spawner_of_an_unknown_type_still_has_a_name_and_icon():
    assert UnknownTypeSpawner.get_display_name() == "test:unknown"
    assert UnknownTypeSpawner.get_icon() == StageObjectSpawner.get_icon()
    assert UnknownTypeSpawner.get_description() == ""


def test_the_note_spawner_creates_a_note_at_the_position_in_one_undo_step(
    stage_editor, actions
):
    undo_count = stage_editor.stage.undo_stack.count()

    note = actions.run_spawner(NoteSpawner, position=QtCore.QPointF(30, 40))

    assert isinstance(note, NoteObject)
    assert note.position == QtCore.QPointF(30, 40)
    assert stage_editor.stage.undo_stack.count() == undo_count + 1
    stage_editor.stage.undo_stack.undo()
    assert util_objects(stage_editor) == []


def test_a_util_object_spawner_honours_the_geometry_and_property_hooks(
    stage_editor, actions
):
    note = actions.run_spawner(StickySpawner, position=QtCore.QPointF(5, 6))

    assert note.position == QtCore.QPointF(15, 16)
    assert note.size == QtCore.QSizeF(100, 80)
    assert note.text == "hello"


def test_the_group_spawner_wraps_the_selected_nodes(stage_editor, actions, create_node):
    a = create_node(stage_editor.stage, "a")
    b = create_node(stage_editor.stage, "b")
    a.set_position(QtCore.QPointF(0, 0))
    b.set_position(QtCore.QPointF(400, 200))
    stage_editor.gr_stage.rebuild_current_scope()
    select_nodes(stage_editor, a, b)
    context = actions.build_spawn_context()

    position, size = GroupSpawner.get_creation_geometry(context)

    nodes_area = context.selection_rect
    assert position == QtCore.QPointF(
        nodes_area.left() - GroupSpawner.MARGIN,
        nodes_area.top() - GroupSpawner.MARGIN - GroupSpawner.TITLE_SPACE,
    )
    assert size == QtCore.QSizeF(
        nodes_area.width() + 2 * GroupSpawner.MARGIN,
        nodes_area.height() + 2 * GroupSpawner.MARGIN + GroupSpawner.TITLE_SPACE,
    )


def test_the_group_spawner_without_a_selection_uses_the_position_and_default_size(
    stage_editor, actions
):
    context = actions.build_spawn_context(QtCore.QPointF(7, 8))

    assert context.selection_rect is None
    assert GroupSpawner.get_creation_geometry(context) == (QtCore.QPointF(7, 8), None)


def test_a_locked_scope_stops_spawners_and_says_so(
    stage_editor, actions, monkeypatch, caplog
):
    monkeypatch.setattr(SpawnContext, "is_scope_locked", property(lambda self: True))
    context = actions.build_spawn_context()
    undo_count = stage_editor.stage.undo_stack.count()

    with caplog.at_level(logging.WARNING):
        created = actions.run_spawner(NoteSpawner, context=context)

    assert not NoteSpawner.is_available(context)
    assert created is None
    assert stage_editor.stage.undo_stack.count() == undo_count
    assert "Can't create note here" in caplog.text


def test_the_created_util_object_is_selected(stage_editor, actions, create_node):
    node = create_node(stage_editor.stage, "a")
    select_nodes(stage_editor, node)

    note = actions.run_spawner(NoteSpawner)

    assert stage_editor.gr_stage.get_gr_util_object(note).isSelected()
    assert stage_editor.list_selected_objects() == [note]


def test_a_created_node_is_selected(stage_editor, actions, register_spawners):
    register_spawners(ActionNodeSpawner)

    node = actions.run_spawner(
        NYX_REGISTRY.get_spawner_cls(ActionNodeSpawner.get_type_id())
    )

    assert node.get_type_id() == CoreNodes.ACTION
    assert stage_editor.list_selected_nodes() == [node]


def test_a_spawner_that_fails_is_reported_and_leaves_the_selection(
    stage_editor, actions, create_node, caplog
):
    node = create_node(stage_editor.stage, "a")
    select_nodes(stage_editor, node)

    with caplog.at_level(logging.WARNING):
        created = actions.run_spawner(FailingSpawner)

    assert created is None
    assert "Can't create failing: no way" in caplog.text
    assert stage_editor.list_selected_nodes() == [node]


def test_running_nothing_does_nothing(actions):
    assert actions.run_spawner(None) is None


def test_the_note_and_group_entries_run_the_registered_actions_and_plugins_get_their_own(
    stage_editor, actions, register_spawners
):
    register_spawners(StickySpawner)
    parent = QtWidgets.QWidget()

    note, group, sticky = actions.build_spawner_actions(parent, QtCore.QPointF(0, 0))[:3]

    assert note.text() == "Note"
    assert note.objectName() == ActionId.CREATE_NOTE
    # The group keeps its shortcut, shown at the right of the entry
    assert group.text().split("\t")[0] == "Group"
    assert group.text().split("\t")[1] == (
        ACTION_REGISTRY.action(ActionId.CREATE_GROUP)
        .shortcut()
        .toString(QtGui.QKeySequence.SequenceFormat.NativeText)
    )
    assert not note.icon().isNull()
    assert sticky.text() == "Sticky"
    assert sticky.toolTip() == "A note with text."
    assert not sticky.icon().isNull()
    assert sticky.isEnabled()
    assert sticky.parent() is parent


def test_the_note_entry_triggers_the_registered_action(stage_editor, actions):
    triggered = []
    registered = ACTION_REGISTRY.action(ActionId.CREATE_NOTE)
    registered.triggered.connect(lambda: triggered.append(True))
    parent = QtWidgets.QWidget()
    note = actions.build_spawner_actions(parent, QtCore.QPointF(0, 0))[0]

    note.trigger()

    assert triggered == [True]


def test_a_proxy_action_copies_the_state_of_its_source(qtbot):
    parent = QtWidgets.QWidget()
    qtbot.addWidget(parent)
    source = QtGui.QAction("Source", parent)
    source.setObjectName("source.id")
    source.setEnabled(False)

    proxy = context_menus.make_proxy_action(parent, source, "Mine")

    assert proxy.text() == "Mine"
    assert proxy.objectName() == "source.id"
    assert not proxy.isEnabled()
    assert proxy.parent() is parent


def test_a_plugin_entry_creates_at_the_position_of_the_menu_not_the_last_hover(
    stage_editor, actions, register_spawners
):
    register_spawners(StickySpawner)
    stage_editor.gr_view.last_scene_mouse_pos = QtCore.QPointF(500, 500)
    parent = QtWidgets.QWidget()
    sticky = actions.build_spawner_actions(parent, QtCore.QPointF(20, 30))[2]

    sticky.trigger()

    (note,) = util_objects(stage_editor)
    assert note.position == QtCore.QPointF(30, 40)


def test_a_plugin_entry_is_disabled_where_nothing_can_be_added(
    stage_editor, actions, register_spawners, monkeypatch
):
    register_spawners(StickySpawner)
    monkeypatch.setattr(SpawnContext, "is_scope_locked", property(lambda self: True))

    parent = QtWidgets.QWidget()
    sticky = actions.build_spawner_actions(parent, QtCore.QPointF(0, 0))[2]

    assert not sticky.isEnabled()


def test_the_create_menu_lists_the_node_then_the_spawners(qtbot):
    parent = QtWidgets.QWidget()
    qtbot.addWidget(parent)
    first = QtGui.QAction("First", parent)
    second = QtGui.QAction("Second", parent)

    menu = context_menus.build_create_menu(parent, [first, second])

    entries = menu.actions()
    assert [entry.text() for entry in entries if not entry.isSeparator()] == [
        "Node...",
        "First",
        "Second",
    ]
    assert entries[1].isSeparator()
    assert entries[0].objectName() == ActionId.CREATE_NODE
    assert not entries[0].icon().isNull()


def test_the_create_menu_without_spawners_has_only_the_node(qtbot):
    parent = QtWidgets.QWidget()
    qtbot.addWidget(parent)

    menu = context_menus.build_create_menu(parent, [])

    assert [entry.text() for entry in menu.actions()] == ["Node..."]


def test_the_graph_context_menu_has_a_create_menu_with_the_spawners(
    stage_editor, register_spawners, monkeypatch
):
    register_spawners(StickySpawner)
    menus = []
    monkeypatch.setattr(
        context_menus, "show_menu", lambda menu, global_pos: menus.append(menu)
    )
    view = stage_editor.gr_view
    point = QtCore.QPoint(5, 5)

    view.show_context_menu(point)

    (menu,) = menus
    (create_action,) = [
        action
        for action in menu.actions()
        if action.objectName() == context_menus.CREATE_MENU_OBJECT_NAME
    ]
    texts = [a.text() for a in create_action.menu().actions() if not a.isSeparator()]
    assert texts[0] == "Node..."
    assert texts[1] == "Note"
    assert texts[-1] == "Sticky"
    sticky = create_action.menu().actions()[-1]
    assert sticky.isEnabled()

    sticky.trigger()

    (note,) = util_objects(stage_editor)
    assert note.position == view.mapToScene(point) + QtCore.QPointF(10, 10)


def test_the_tree_context_menu_has_no_create_menu(
    main_window, stage_editor, monkeypatch
):
    menus = []
    monkeypatch.setattr(
        context_menus, "show_menu", lambda menu, global_pos: menus.append(menu)
    )

    main_window.stage_tree_view.show_context_menu(QtCore.QPoint(5, 5))

    names = [action.objectName() for action in menus[0].actions()]
    assert context_menus.CREATE_MENU_OBJECT_NAME not in names
    assert ActionId.CREATE_NODE in names
