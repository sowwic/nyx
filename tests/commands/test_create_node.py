import pytest
import logging
from nyx.core.stage import Stage
from nyx.core.commands import CreateNodeCommand
from nyx.core.exceptions import NyxCommandValidationError

LOGGER = logging.getLogger(__name__)


def test_default_node_creation():
    """Test creating a node with default parameters."""
    stage = Stage()
    command = CreateNodeCommand(stage=stage)
    stage.push_command(command)
    expected_path = "/node"

    assert stage.node(expected_path) is not None


def test_node_creation_with_custom_name():
    """Test creating a node with a custom name."""
    stage = Stage()
    command = CreateNodeCommand(stage=stage, node_name="custom_node")
    stage.push_command(command)
    expected_path = "/custom_node"

    assert stage.node(expected_path) is not None


def test_node_creation_with_position_tuple():
    """Test creating a node with a specified position."""
    stage = Stage()
    command = CreateNodeCommand(
        stage=stage, node_name="positioned_node", position=(1.0, 5.0)
    )
    stage.push_command(command)
    expected_path = "/positioned_node"

    node = stage.node(expected_path)
    assert pytest.approx(node.position().x()) == 1.0
    assert pytest.approx(node.position().y()) == 5.0


def test_node_creation_with_parent():
    """Test creating a node with a parent path."""
    stage = Stage()
    parent_command = CreateNodeCommand(stage=stage, node_name="parent_node")
    stage.push_command(parent_command)

    child_command = CreateNodeCommand(
        stage=stage, parent_path="/parent_node", node_name="child_node"
    )
    stage.push_command(child_command)

    expected_parent_path = "/parent_node"
    expected_child_path = "/parent_node/child_node"

    assert stage.node(expected_parent_path) is not None
    assert stage.node(expected_child_path) is not None


def test_node_creation_with_invalid_parent_raises_validation_error():
    """Test that creating a node with a non-existent parent raises error."""
    stage = Stage()
    command = CreateNodeCommand(stage=stage, parent_path="/non_existent_parent")
    with pytest.raises(NyxCommandValidationError):
        stage.push_command(command)


def test_node_creation_undo_redo():
    """Test undo and redo of node creation."""
    stage = Stage()
    expected_path = "/test_node"
    command = CreateNodeCommand(stage=stage, node_name="test_node")

    stage.push_command(command)
    assert stage.node(expected_path) is not None
    stage.undo_stack.undo()
    assert stage.node(expected_path) is None
    stage.undo_stack.redo()
    assert stage.node(expected_path) is not None


def test_node_creation_with_duplicate_name():
    """Test creating nodes with duplicate names under the same parent."""
    stage = Stage()

    for i in range(3):
        command = CreateNodeCommand(stage=stage, node_name="node1")
        stage.push_command(command)

    expected_path1 = "/node1"
    expected_path2 = "/node11"
    expected_path3 = "/node12"
    assert stage.node(expected_path1) is not None
    assert stage.node(expected_path2) is not None
    assert stage.node(expected_path3) is not None
