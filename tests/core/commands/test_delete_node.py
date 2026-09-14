import logging

import pytest

from nyx.core.commands import CreateNodeCommand, DeleteNodeCommand
from nyx.core.exceptions import NyxCommandValidationError
from nyx.core.stage import Stage

LOGGER = logging.getLogger(__name__)


def test_node_deletion():
    """Test deleting a node."""
    stage = Stage()
    test_path = stage.ROOT_NODE_PATH / "node_to_delete"
    # Create a node to delete
    create_command = CreateNodeCommand(stage=stage, node_name=test_path.name)
    stage.push_command(create_command)
    assert stage.node(test_path) is not None

    # Now delete the node
    delete_command = DeleteNodeCommand(stage=stage, nodes=[test_path])
    stage.push_command(delete_command)

    assert stage.node(test_path) is None


def test_delete_undo_redo():
    """Test undo and redo of node deletion."""
    stage = Stage()
    test_path = stage.ROOT_NODE_PATH / "node_to_delete"
    # Create a node to delete
    create_command = CreateNodeCommand(stage=stage, node_name=test_path.name)
    stage.push_command(create_command)

    # Delete the node
    delete_command = DeleteNodeCommand(stage=stage, nodes=[test_path])
    stage.push_command(delete_command)

    # Undo the deletion
    stage.undo_stack.undo()
    assert stage.node(test_path) is not None

    # Redo the deletion
    stage.undo_stack.redo()
    assert stage.node(test_path) is None


def test_delete_multiple_nodes():
    """Test deleting multiple nodes."""
    stage = Stage()
    # Create multiple nodes to delete
    for i in range(3):
        create_command = CreateNodeCommand(stage=stage, node_name=f"node_{i}")
        stage.push_command(create_command)

    # Delete the nodes
    delete_command = DeleteNodeCommand(
        stage=stage, nodes=[f"/node_{i}" for i in range(3)]
    )
    stage.push_command(delete_command)

    for i in range(3):
        assert stage.node(f"/node_{i}") is None


def test_delete_parent_node():
    """Test deleting a parent node also deletes its children."""
    stage = Stage()
    # Create a parent node and a child node
    create_parent_command = CreateNodeCommand(stage=stage, node_name="parent_node")
    stage.push_command(create_parent_command)

    create_child_command = CreateNodeCommand(
        stage=stage, parent_path="/parent_node", node_name="child_node"
    )
    stage.push_command(create_child_command)

    # Delete the parent node
    delete_command = DeleteNodeCommand(stage=stage, nodes=["/parent_node"])
    stage.push_command(delete_command)

    assert stage.node("/parent_node") is None
    assert stage.node("/parent_node/child_node") is None

    stage.undo_stack.undo()  # Undo delete
    assert stage.node("/parent_node") is not None
    assert stage.node("/parent_node/child_node") is not None


def test_delete_non_existent_node_raises_validation_error() -> None:
    """Test deleting a non existing node raises a validation error"""
    stage = Stage()
    # Delete the parent node
    delete_command = DeleteNodeCommand(stage=stage, nodes=["/test_node"])
    with pytest.raises(NyxCommandValidationError):
        stage.push_command(delete_command)
