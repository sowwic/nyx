import logging

import pytest

from nyx.core.commands import CreateNodeCommand
from nyx.api.v1 import Stage, exceptions


LOGGER = logging.getLogger(__name__)


def test_default_node_creation():
    """Test creating a node with default parameters."""
    stage = Stage()
    command = CreateNodeCommand(stage=stage)
    stage.push_command(command)
    expected_path = stage.root_node.path / "node"

    assert stage.get_object(expected_path) is not None


def test_node_creation_with_custom_name():
    """Test creating a node with a custom name."""
    stage = Stage()
    command = CreateNodeCommand(stage=stage, name="custom_node")
    stage.push_command(command)
    expected_path = stage.root_node.path / "custom_node"

    assert stage.get_object(expected_path) is not None


def test_node_creation_with_position_tuple():
    """Test creating a node with a specified position."""
    stage = Stage()
    command = CreateNodeCommand(stage=stage, name="positioned_node", position=(1.0, 5.0))
    stage.push_command(command)
    expected_path = stage.root_node.path / "positioned_node"

    node = stage.get_object(expected_path)
    assert pytest.approx(node.position().x()) == 1.0
    assert pytest.approx(node.position().y()) == 5.0


def test_node_creation_with_parent():
    """Test creating a node with a parent path."""
    stage = Stage()
    parent_command = CreateNodeCommand(stage=stage, name="parent_node")
    stage.push_command(parent_command)
    parent_path = stage.root_node.path / "parent_node"
    child_path = parent_path / "child_node"

    child_command = CreateNodeCommand(
        stage=stage,
        parent_node=stage.root_node.path / "parent_node",
        name=child_path.name,
    )
    stage.push_command(child_command)

    assert stage.get_object(parent_path) is not None
    assert stage.get_object(child_path) is not None


def test_node_creation_with_invalid_parent_raises_validation_error():
    """Test that creating a node with a non-existent parent raises error."""
    stage = Stage()
    with pytest.raises(exceptions.StageObjectQueryError):
        command = CreateNodeCommand(stage=stage, parent_node="/non_existent_parent")
        stage.push_command(command)


def test_node_creation_undo_redo():
    """Test undo and redo of node creation."""
    stage = Stage()
    expected_path = stage.root_node.path / "test_node"
    command = CreateNodeCommand(stage=stage, name=expected_path.name)

    stage.push_command(command)
    uuid_on_creation = command.result_node.uuid

    assert stage.get_object(expected_path) is not None
    stage.undo_stack.undo()
    with pytest.raises(exceptions.StageObjectQueryError):
        stage.get_object(expected_path)
    stage.undo_stack.redo()

    assert stage.get_object(expected_path) is not None
    assert stage.get_object(expected_path).uuid == uuid_on_creation


def test_node_creation_with_duplicate_name():
    """Test creating nodes with duplicate names under the same parent."""
    stage = Stage()

    for _ in range(3):
        command = CreateNodeCommand(stage=stage, name="node1")
        stage.push_command(command)

    expected_path1 = "/stage/node1"
    expected_path2 = "/stage/node11"
    expected_path3 = "/stage/node12"
    assert stage.get_object(expected_path1) is not None
    assert stage.get_object(expected_path2) is not None
    assert stage.get_object(expected_path3) is not None
