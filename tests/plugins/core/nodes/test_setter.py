import pytest
import typing
from nyx.api.v1 import Stage, CoreNodes, CoreNodeComponents, commands, exceptions

if typing.TYPE_CHECKING:
    from nyx.plugins.core.nodes.setter import SetterNode


def test_setter_creation():
    """Test creating new log node with default parameters."""
    stage = Stage()
    command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.SET)
    stage.push_command(command)
    result_node: SetterNode = stage.get_object(command.result_node.uuid)

    assert result_node.components_model.rowCount() == 3

    flow = result_node["flow"]
    assert flow.get_type_id() == CoreNodeComponents.FLOW
    assert flow.accepts_input is True
    assert flow.produces_output is True

    in_component_path = result_node["component"]
    assert in_component_path.get_type_id() == CoreNodeComponents.STAGE_REFERENCE
    assert in_component_path.is_editable is True
    assert in_component_path.accepts_input is True
    assert in_component_path.produces_output is False

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
    setter_node["component"].push_value(f"{log_node.path}.message")
    setter_node["value"].push_value(request.node.name)

    assert log_node["message"].pull_value() == ""
    stage.crawler.start(start_node=setter_node)

    assert log_node["message"].pull_value() == request.node.name


def test_setter_accepts_relative_component_path():
    stage = Stage()
    log_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.LOG)
    stage.push_command(log_command)
    setter_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.SET)
    stage.push_command(setter_command)
    log_node, setter_node = log_command.result_node, setter_command.result_node

    setter_node["component"].push_value(f"./{log_node.name}.message")
    setter_node["value"].push_value("changed")
    setter_node.execute()

    assert log_node["message"].pull_value() == "changed"


def test_setter_with_missing_component_raises():
    stage = Stage()
    setter_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.SET)
    stage.push_command(setter_command)
    setter_node = setter_command.result_node

    setter_node["component"].push_value("/stage/missing.message")
    with pytest.raises(exceptions.StageObjectQueryError):
        setter_node.execute()
