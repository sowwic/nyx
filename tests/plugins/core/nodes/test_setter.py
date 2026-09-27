import pytest
import typing
from nyx.api.v1 import Stage, CoreNodes, CoreNodeComponents, commands, static_vars

if typing.TYPE_CHECKING:
    from nyx.plugins.core.nodes.setter import SetterNode


def test_setter_creation():
    """Test creating new log node with default parameters."""
    stage = Stage()
    command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.SET)
    stage.push_command(command)
    result_node: SetterNode = stage.get_object(command.result_node.uuid)

    assert result_node.components_model.rowCount() == 4

    flow = result_node["flow"]
    assert flow.get_type_id() == CoreNodeComponents.FLOW
    assert flow.accepts_input is True
    assert flow.produces_output is True

    in_node_path = result_node["node_path"]
    assert in_node_path.get_type_id() == CoreNodeComponents.VALUE
    assert in_node_path.default_value == static_vars.ROOT_NODE_PATH.as_posix()
    assert in_node_path.is_editable is True
    assert in_node_path.accepts_input is True
    assert in_node_path.produces_output is False

    in_cpnt_name = result_node["cpnt_name"]
    assert in_cpnt_name.get_type_id() == CoreNodeComponents.VALUE
    assert in_cpnt_name.is_editable is True
    assert in_cpnt_name.accepts_input is True
    assert in_cpnt_name.produces_output is False

    in_value = result_node["value"]
    assert in_value.get_type_id() == CoreNodeComponents.VALUE
    assert in_value.accepts_input is True
    assert in_value.produces_output is False


def test_setter_execution_sets_component_value(request: pytest.FixtureRequest):
    """Check logger post components execution"""
    stage = Stage()
    log_node_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.LOG)
    stage.push_command(log_node_command)
    log_node = log_node_command.result_node

    setter_node_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.SET)
    stage.push_command(setter_node_command)

    setter_node: SetterNode = setter_node_command.result_node
    setter_node["node_path"].value = str(log_node.path)
    setter_node["cpnt_name"].value = "message"
    setter_node["value"].value = request.node.name

    assert log_node["message"].value == ""
    stage.crawler.start(start_node=setter_node)

    assert log_node["message"].value == request.node.name
