import logging
import pytest


from nyx.core.commands import (
    AddNodeComponentCommand,
    CreateNodeCommand,
    DeleteNodeComponentCommand,
    LinkNodeComponentsCommand,
)
from nyx.api.v1 import Stage, CoreNodes, CoreNodeComponents


LOGGER = logging.getLogger(__name__)


def test_delete_node_component():
    """Test creating a node with default parameters."""
    test_cpnt_type_id = CoreNodeComponents.VALUE
    test_cpnt_name = "test_value_cpnt"

    stage = Stage()
    node_create_command = CreateNodeCommand(stage=stage)
    stage.push_command(node_create_command)
    node = stage.get_object(node_create_command.result_node.uuid)

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
    test_cpnt_type_id = CoreNodeComponents.VALUE
    test_cpnt_name = "test_value_cpnt"

    stage = Stage()
    node_create_command = CreateNodeCommand(stage=stage)
    stage.push_command(node_create_command)
    node = stage.get_object(node_create_command.result_node.uuid)

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
    test_cpnt_type_id = CoreNodeComponents.VALUE
    test_cpnt_name = "test_value_cpnt"

    stage = Stage()
    node_create_command = CreateNodeCommand(stage=stage)
    stage.push_command(node_create_command)
    node = stage.get_object(node_create_command.result_node.uuid)

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


def test_deleting_linked_componet_deletes_link():
    stage = Stage()

    # Create two action nodes
    action1_command = CreateNodeCommand(
        stage=stage, type_id=CoreNodes.ACTION, name="action_one"
    )
    action2_command = CreateNodeCommand(
        stage=stage, type_id=CoreNodes.ACTION, name="action_two"
    )
    stage.push_command(action1_command, action2_command)

    # Add Value components to both
    add_cpnt1_command = AddNodeComponentCommand(
        node=action1_command.result_node, type_id=CoreNodeComponents.VALUE, name="test1"
    )
    add_cpnt2_command = AddNodeComponentCommand(
        node=action2_command.result_node, type_id=CoreNodeComponents.VALUE, name="test2"
    )

    stage.push_command(add_cpnt1_command, add_cpnt2_command)
    add_cpnt1_command.result_component.produces_output = True
    add_cpnt2_command.result_component.accepts_input = True

    # Create links between new value components
    link1_command = LinkNodeComponentsCommand(
        stage=stage,
        source=action1_command.result_node["test1"],
        target=action2_command.result_node["test2"],
    )
    stage.push_command(link1_command)

    assert action1_command.result_node["test1"].is_linked_to(
        action2_command.result_node["test2"], as_source=True
    )
    assert len(stage.collect_links()) == 1

    link_uuid_pre_redo = link1_command.result_link_uuid
    cpnt1_uuid_pre_redo = add_cpnt1_command.result_component.uuid

    # Delete value component one action one
    delete_cpnt_command = DeleteNodeComponentCommand(
        node=action1_command.result_node, name=add_cpnt1_command.result_component.name
    )
    stage.push_command(delete_cpnt_command)
    # Expected: link should be disconnected and not present in stage uuid_map
    assert len(stage.collect_links()) == 0
    assert link_uuid_pre_redo not in stage.uuid_map
    assert link_uuid_pre_redo not in add_cpnt2_command.result_component.links_uuids

    # Undo component deletion - link must be brought back
    stage.undo_stack.undo()
    assert cpnt1_uuid_pre_redo == add_cpnt1_command.result_component.uuid
    assert action1_command.result_node["test1"].is_linked_to(
        action2_command.result_node["test2"], as_source=True
    )
    assert len(stage.collect_links()) == 1
