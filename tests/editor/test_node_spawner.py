import pytest
from PySide6 import QtCore

from nyx.api.v1 import CoreNodes
from nyx.editor.controllers.node_spawner import NodeSpawner


@pytest.fixture
def node_spawner(main_window):
    return NodeSpawner()


def test_spawn_position_validates_type(node_spawner):
    assert node_spawner.spawn_position is None
    node_spawner.spawn_position = QtCore.QPointF(1, 2)
    assert node_spawner.spawn_position == QtCore.QPointF(1, 2)
    node_spawner.spawn_position = None
    assert node_spawner.spawn_position is None
    with pytest.raises(TypeError):
        node_spawner.spawn_position = (1, 2)


def test_spawn_without_stage_graph_returns_none(node_spawner, main_window):
    assert main_window.current_stage_graph is None
    assert node_spawner.spawnNode(CoreNodes.EMPTY) is None


def test_spawn_node_creates_node_at_explicit_position(node_spawner, stage_editor, qtbot):
    position = QtCore.QPointF(120, 80)
    with qtbot.waitSignal(node_spawner.nodeSpawned, timeout=1000) as blocker:
        node = node_spawner.spawnNode(CoreNodes.EMPTY, position)

    assert blocker.args == [node]
    assert node in stage_editor.stage.list_children(stage_editor.stage.root_node)
    assert node.position() == position


def test_spawn_uses_stored_spawn_position(node_spawner, stage_editor):
    node_spawner.spawn_position = QtCore.QPointF(10, 20)
    node = node_spawner.spawnNode(CoreNodes.EMPTY)
    assert node.position() == QtCore.QPointF(10, 20)


def test_spawn_at_center_clears_stored_position(node_spawner, stage_editor):
    node_spawner.spawn_position = QtCore.QPointF(10, 20)
    node = node_spawner.spawnNodeAtCenter(CoreNodes.EMPTY)
    assert node_spawner.spawn_position is None
    assert node.position() == stage_editor.gr_view.get_center_position()


def test_spawn_goes_into_current_scope(node_spawner, stage_editor, create_node):
    parent = create_node(stage_editor.stage, "scope")
    stage_editor.set_scope_path(parent)
    node = node_spawner.spawnNode(CoreNodes.EMPTY)
    assert node.path.parent == parent.path


def test_spawn_is_undoable(node_spawner, stage_editor):
    node = node_spawner.spawnNode(CoreNodes.EMPTY)
    stage_editor.stage.undo_stack.undo()
    assert node not in stage_editor.stage.list_children(stage_editor.stage.root_node)
