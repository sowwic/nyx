import logging


from nyx.core.commands import AddNodeComponentCommand, CreateNodeCommand
from nyx.core.exceptions import NyxCommandValidationError
from nyx.core.stage import Stage


LOGGER = logging.getLogger(__name__)


def test_add_component_with_default_name():
    """Test creating a node with default parameters."""
    test_cpnt_type_id = "core:value"
    stage = Stage()
    node_create_command = CreateNodeCommand(stage=stage)
    stage.push_command(node_create_command)
    node = stage.node(node_create_command.node_path)

    add_cpnt_command = AddNodeComponentCommand(node=node, type_id=test_cpnt_type_id)
    stage.push_command(add_cpnt_command)

    value_cpnt = next(
        node.components_model.find_components_of_type(type_id=test_cpnt_type_id), None
    )
    assert value_cpnt is not None
    assert value_cpnt.type_id == test_cpnt_type_id
    assert value_cpnt.name == value_cpnt.DEFAULT_NAME


def test_add_component_with_custom_name():
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

    value_cpnt = node[test_cpnt_name]
    assert value_cpnt is not None
    assert value_cpnt.type_id == test_cpnt_type_id
    assert value_cpnt.name == test_cpnt_name


def test_add_component_undo():
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

    assert node[test_cpnt_name] is not None

    stage.undo_stack.undo()
    assert node[test_cpnt_name] is None
    assert node.components_model.rowCount() == 0


def test_add_component_undo_redo():
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

    assert node[test_cpnt_name] is not None

    stage.undo_stack.undo()
    assert node[test_cpnt_name] is None
    assert node.components_model.rowCount() == 0

    stage.undo_stack.redo()
    assert node[test_cpnt_name] is not None
