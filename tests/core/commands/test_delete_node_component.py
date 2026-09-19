import logging
import pytest


from nyx.core.commands import (
    AddNodeComponentCommand,
    CreateNodeCommand,
    DeleteNodeComponentCommand,
)
from nyx.core.stage import Stage


LOGGER = logging.getLogger(__name__)


def test_delete_node_component():
    """Test creating a node with default parameters."""
    test_cpnt_type_id = "core:value"
    test_cpnt_name = "test_value_cpnt"

    stage = Stage()
    node_create_command = CreateNodeCommand(stage=stage)
    stage.push_command(node_create_command)
    node = stage.node(node_create_command.node_path)

    add_cpnt_command = AddNodeComponentCommand(
        node=node, type_id=test_cpnt_type_id, name=test_cpnt_name
    )
    stage.push_command(add_cpnt_command)

    assert node is not None
    assert node[test_cpnt_name] is not None

    delete_cpnt_command = DeleteNodeComponentCommand(node=node, name=test_cpnt_name)
    stage.push_command(delete_cpnt_command)
    with pytest.raises(ValueError):
        node[test_cpnt_name]


def test_delete_node_component_undo():
    """Test creating a node with default parameters."""
    test_cpnt_type_id = "core:value"
    test_cpnt_name = "test_value_cpnt"

    stage = Stage()
    node_create_command = CreateNodeCommand(stage=stage)
    stage.push_command(node_create_command)
    node = stage.node(node_create_command.node_path)

    add_cpnt_command = AddNodeComponentCommand(
        node=node, type_id=test_cpnt_type_id, name=test_cpnt_name
    )
    stage.push_command(add_cpnt_command)

    assert node is not None
    assert node[test_cpnt_name] is not None

    delete_cpnt_command = DeleteNodeComponentCommand(node=node, name=test_cpnt_name)
    stage.push_command(delete_cpnt_command)
    with pytest.raises(ValueError, match="has no component"):
        assert node[test_cpnt_name] is None

    stage.undo_stack.undo()
    assert node[test_cpnt_name] is not None


def test_delete_node_component_undo_redo():
    """Test creating a node with default parameters."""
    test_cpnt_type_id = "core:value"
    test_cpnt_name = "test_value_cpnt"

    stage = Stage()
    node_create_command = CreateNodeCommand(stage=stage)
    stage.push_command(node_create_command)
    node = stage.node(node_create_command.node_path)

    add_cpnt_command = AddNodeComponentCommand(
        node=node, type_id=test_cpnt_type_id, name=test_cpnt_name
    )
    stage.push_command(add_cpnt_command)

    assert node is not None
    assert node[test_cpnt_name] is not None

    delete_cpnt_command = DeleteNodeComponentCommand(node=node, name=test_cpnt_name)
    stage.push_command(delete_cpnt_command)
    with pytest.raises(ValueError, match="has no component"):
        node[test_cpnt_name]

    stage.undo_stack.undo()
    assert node[test_cpnt_name] is not None

    stage.undo_stack.redo()
    with pytest.raises(ValueError, match="has no component"):
        assert node[test_cpnt_name]
