import logging

import pytest

from nyx.core.commands import CreateNodeCommand, DeleteNodeCommand
from nyx.core.exceptions import NyxCommandValidationError, StageObjectQueryError
from nyx.api.v1 import Stage, CoreNodes

LOGGER = logging.getLogger(__name__)


def test_node_deletion():
    """Test deleting a node."""
    stage = Stage()
    test_path = stage.root_node.path / "node_to_delete"
    # Create a node to delete
    create_command = CreateNodeCommand(stage=stage, name=test_path.name)
    stage.push_command(create_command)
    assert stage.get_object(test_path) is not None

    # Now delete the node
    delete_command = DeleteNodeCommand(stage=stage, nodes=[test_path])
    stage.push_command(delete_command)

    with pytest.raises(StageObjectQueryError):
        stage.get_object(test_path)


def test_delete_undo_redo():
    """Test undo and redo of node deletion."""
    stage = Stage()
    test_path = stage.root_node.path / "node_to_delete"
    test_type_id = CoreNodes.ACTION
    # Create a node to delete
    create_command = CreateNodeCommand(
        stage=stage, name=test_path.name, type_id=test_type_id
    )
    stage.push_command(create_command)

    uuid_on_creation = create_command.result_node.uuid

    # Delete the node
    delete_command = DeleteNodeCommand(stage=stage, nodes=[test_path])
    stage.push_command(delete_command)

    # Undo the deletion
    stage.undo_stack.undo()
    assert stage.get_object(test_path) is not None
    assert stage.get_object(test_path).get_type_id() == test_type_id
    assert stage.get_object(test_path).uuid == uuid_on_creation

    # Redo the deletion
    stage.undo_stack.redo()
    with pytest.raises(StageObjectQueryError):
        stage.get_object(test_path)


def test_delete_multiple_nodes():
    """Test deleting multiple nodes."""
    stage = Stage()
    # Create multiple nodes to delete
    for i in range(3):
        create_command = CreateNodeCommand(stage=stage, name=f"node_{i}")
        stage.push_command(create_command)

    # Delete the nodes
    delete_command = DeleteNodeCommand(
        stage=stage, nodes=[stage.root_node.path / f"node_{i}" for i in range(3)]
    )
    stage.push_command(delete_command)

    for i in range(3):
        with pytest.raises(StageObjectQueryError):
            assert stage.get_object(stage.root_node.path / f"node_{i}") is None


def test_delete_parent_node():
    """Test deleting a parent node also deletes its children."""
    stage = Stage()
    parent_path = stage.root_node.path / "parent_node"
    child_path = parent_path / "child_node"
    # Create a parent node and a child node
    create_parent_command = CreateNodeCommand(stage=stage, name="parent_node")
    stage.push_command(create_parent_command)

    create_child_command = CreateNodeCommand(
        stage=stage, parent_node=parent_path, name="child_node"
    )
    stage.push_command(create_child_command)

    # Delete the parent node
    delete_command = DeleteNodeCommand(stage=stage, nodes=[parent_path])
    stage.push_command(delete_command)

    with pytest.raises(StageObjectQueryError):
        assert stage.get_object(parent_path) is None
        assert stage.get_object(child_path) is None

    stage.undo_stack.undo()  # Undo delete
    assert stage.get_object(parent_path) is not None
    assert stage.get_object(child_path) is not None


def test_delete_non_existent_node_raises_validation_error() -> None:
    """Test deleting a non existing node raises a validation error"""
    stage = Stage()
    # Delete the parent node
    delete_command = DeleteNodeCommand(stage=stage, nodes=["/test_node"])
    with pytest.raises(NyxCommandValidationError):
        stage.push_command(delete_command)
