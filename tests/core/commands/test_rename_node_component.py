import logging

from nyx.api.v1 import Stage, CoreNodeComponents
from nyx.api.v1 import commands


LOGGER = logging.getLogger(__name__)


def test_rename_component():
    """Test creating a node with default parameters."""
    stage = Stage()
    node_create_command = commands.CreateNodeCommand(stage=stage)
    stage.push_command(node_create_command)
    node = stage.get_object(node_create_command.result_node.uuid)

    add_cpnt_command = commands.AddNodeComponentCommand(
        node=node, type_id=CoreNodeComponents.VALUE
    )
    stage.push_command(add_cpnt_command)

    value_cpnt = next(
        node.components_model.find_components_of_type(type_id=CoreNodeComponents.VALUE),
        None,
    )
    assert value_cpnt is not None

    new_name = "test_new_name"
    rename_component_command = commands.RenameNodeComponentCommand(
        stage=stage, node_component=value_cpnt, new_name=new_name
    )
    stage.push_command(rename_component_command)
    assert value_cpnt.name == new_name


def test_rename_component_undo():
    """Test creating a node with default parameters."""
    stage = Stage()
    node_create_command = commands.CreateNodeCommand(stage=stage)
    stage.push_command(node_create_command)
    node = stage.get_object(node_create_command.result_node.uuid)

    add_cpnt_command = commands.AddNodeComponentCommand(
        node=node, type_id=CoreNodeComponents.VALUE
    )
    stage.push_command(add_cpnt_command)

    value_cpnt = next(
        node.components_model.find_components_of_type(type_id=CoreNodeComponents.VALUE),
        None,
    )
    assert value_cpnt is not None

    new_name = "test_new_name"
    old_name = value_cpnt.name
    rename_component_command = commands.RenameNodeComponentCommand(
        stage=stage, node_component=value_cpnt, new_name=new_name
    )
    stage.push_command(rename_component_command)
    assert value_cpnt.name == new_name

    stage.undo_stack.undo()
    assert value_cpnt.name == old_name
