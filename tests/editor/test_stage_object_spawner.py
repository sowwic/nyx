import logging

import pytest
from PySide6 import QtCore

from nyx.api.v1 import CoreNodeComponents, CoreNodes, CoreUtilObjects, commands
from nyx.core.exceptions import NyxCommandValidationError
from nyx.api.v1.editor_utils import SpawnContext, StageObjectSpawner, UtilObjectSpawner
from nyx.editor.controllers.components_spawner import NodeComponentSpawner
from nyx.editor.controllers.node_spawner import NodeSpawner
from nyx.stdlib.spawners.note import NoteSpawner


class LabelledNoteSpawner(UtilObjectSpawner):
    @classmethod
    def get_type_id(cls) -> str:
        return "test.labelled_note"

    @classmethod
    def get_util_object_type_id(cls) -> str:
        return CoreUtilObjects.NOTE

    @classmethod
    def get_creation_geometry(cls, context):
        return context.position + QtCore.QPointF(5, 5), QtCore.QSizeF(90, 70)

    @classmethod
    def get_creation_properties(cls, context):
        return {"text": "labelled"}


def record(signal):
    received = []
    signal.connect(received.append)
    return received


def spawn_context(editor, position=QtCore.QPointF(10, 20)):
    return SpawnContext(
        graph_editor=editor,
        stage=editor.stage,
        scope_node=editor.stage.root_node,
        position=position,
    )


# ---- The family ----
def test_the_spawners_share_one_base():
    for spawner_cls in (NodeSpawner, NodeComponentSpawner, UtilObjectSpawner):
        assert issubclass(spawner_cls, StageObjectSpawner)
    assert issubclass(NoteSpawner, UtilObjectSpawner)


def test_the_menu_contract_has_defaults_and_requires_the_rest(stage_editor):
    spawner = StageObjectSpawner()

    assert spawner.get_icon() == ":/icons/plus"
    assert spawner.get_description() == ""
    assert spawner.is_available(spawn_context(stage_editor))
    for method in (spawner.get_type_id, spawner.get_display_name):
        with pytest.raises(NotImplementedError):
            method()
    with pytest.raises(NotImplementedError):
        spawner.spawn(spawn_context(stage_editor))


# ---- The base: push the command and report ----
def test_spawn_returns_the_result_and_emits_spawned(stage_editor):
    spawner = StageObjectSpawner()
    spawned = record(spawner.spawned)
    command = commands.CreateNodeCommand(
        stage=stage_editor.stage, type_id=CoreNodes.EMPTY, name="made"
    )

    node = spawner._spawn(stage_editor.stage, command, lambda: command.result_node)

    assert node.name == "made"
    assert spawned == [node]


def test_a_refused_command_gives_a_warning_and_nothing_else(stage_editor, caplog):
    spawner = StageObjectSpawner()
    spawned = record(spawner.spawned)
    undo_count = stage_editor.stage.undo_stack.count()
    command = commands.CreateNodeCommand(
        stage=stage_editor.stage, type_id="test:unknown", name="never"
    )

    with caplog.at_level(logging.WARNING):
        node = spawner._spawn(stage_editor.stage, command, lambda: command.result_node)

    assert node is None
    assert spawned == []
    assert "Invalid node type_id: test:unknown" in caplog.text
    assert stage_editor.stage.undo_stack.count() == undo_count


# ---- NodeSpawner ----
def test_the_node_spawner_emits_both_signals(stage_editor):
    spawner = NodeSpawner()
    spawned, node_spawned = record(spawner.spawned), record(spawner.nodeSpawned)

    node = spawner.spawnNode(CoreNodes.EMPTY, QtCore.QPointF(1, 2))

    assert spawned == [node]
    assert node_spawned == [node]


def test_the_node_spawner_does_not_raise_for_a_node_that_is_refused(
    stage_editor, caplog, monkeypatch
):
    def refuse(self):
        raise NyxCommandValidationError("the scope is locked")

    monkeypatch.setattr(commands.CreateNodeCommand, "validate", refuse)
    spawner = NodeSpawner()
    node_spawned = record(spawner.nodeSpawned)

    with caplog.at_level(logging.WARNING):
        node = spawner.spawnNode(CoreNodes.EMPTY)

    assert node is None
    assert node_spawned == []
    assert "the scope is locked" in caplog.text


# ---- NodeComponentSpawner ----
def test_the_component_spawner_emits_both_signals(stage_editor, create_node):
    node = create_node(stage_editor.stage, "target", type_id=CoreNodes.EMPTY)
    spawner = NodeComponentSpawner()
    spawned, component_spawned = (
        record(spawner.spawned),
        record(spawner.componentSpawned),
    )

    component = spawner.spawnComponent(CoreNodeComponents.VALUE, node)

    assert component is not None
    assert spawned == [component]
    assert component_spawned == [component]


def test_the_component_spawner_reports_a_component_that_is_refused(
    stage_editor, create_node, caplog
):
    node = create_node(stage_editor.stage, "target", type_id=CoreNodes.EMPTY)
    spawner = NodeComponentSpawner()
    spawned = record(spawner.spawned)

    with caplog.at_level(logging.WARNING):
        component = spawner.spawnComponent("test:unknown", node)

    assert component is None
    assert spawned == []
    assert "Invalid type_id" in caplog.text


# ---- UtilObjectSpawner ----
def test_the_util_object_spawner_returns_the_object_and_emits_spawned(stage_editor):
    spawner = NoteSpawner(stage_editor.gr_view)
    spawned = record(spawner.spawned)

    note = spawner.spawn(spawn_context(stage_editor, QtCore.QPointF(30, 40)))

    assert note.position == QtCore.QPointF(30, 40)
    assert spawned == [note]
    assert note in stage_editor.stage.root_node.util_objects


def test_the_util_object_spawner_honours_the_hooks(stage_editor):
    spawner = LabelledNoteSpawner(stage_editor.gr_view)

    note = spawner.spawn(spawn_context(stage_editor, QtCore.QPointF(10, 20)))

    assert note.position == QtCore.QPointF(15, 25)
    assert note.size == QtCore.QSizeF(90, 70)
    assert note.text == "labelled"


def test_the_util_object_spawner_reports_a_type_that_is_refused(stage_editor, caplog):
    class UnknownTypeSpawner(UtilObjectSpawner):
        @classmethod
        def get_type_id(cls) -> str:
            return "test.unknown_type_spawner"

        @classmethod
        def get_util_object_type_id(cls) -> str:
            return "test:unknown"

    spawner = UnknownTypeSpawner(stage_editor.gr_view)
    spawned = record(spawner.spawned)

    with caplog.at_level(logging.WARNING):
        created = spawner.spawn(spawn_context(stage_editor))

    assert created is None
    assert spawned == []
    assert caplog.records  # the refusal was logged
