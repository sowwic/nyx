import pathlib
import pytest
import typing
from nyx.api.v1 import Stage, CoreNodes, CoreNodeComponents, commands, static_vars

if typing.TYPE_CHECKING:
    from nyx.plugins.core.nodes.getter import GetterNode
    from nyx.plugins.core.nodes.setter import SetterNode


def test_getter_creation():
    """Test creating new log node with default parameters."""
    stage = Stage()
    command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.GET)
    stage.push_command(command)
    result_node: GetterNode = stage.get_object(command.result_node.uuid)

    assert result_node.components_model.rowCount() == 3

    in_node_path = result_node["node_path"]
    assert in_node_path.get_type_id() == CoreNodeComponents.VALUE
    assert in_node_path.default_value == static_vars.ROOT_NODE_PATH.as_posix()
    assert in_node_path.is_editable is True
    assert in_node_path.accepts_input is False
    assert in_node_path.produces_output is False

    in_cpnt_name = result_node["cpnt_name"]
    assert in_cpnt_name.get_type_id() == CoreNodeComponents.VALUE
    assert in_cpnt_name.is_editable is True
    assert in_cpnt_name.accepts_input is False
    assert in_cpnt_name.produces_output is False

    in_value = result_node["value"]
    assert in_value.get_type_id() == CoreNodeComponents.VALUE
    assert in_value.accepts_input is False
    assert in_value.produces_output is True


def test_getter_can_be_used_to_pull_values(
    output_dir: pathlib.Path, request: pytest.FixtureRequest
):
    """Check logger post components execution"""
    stage = Stage()
    export_path = output_dir / f"{request.node.name}_export{stage.FILE_EXTENSION}"
    log_node_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.LOG)
    stage.push_command(log_node_command)
    log_node = log_node_command.result_node
    log_node["message"].push_value(request.node.name)

    setter_node_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.SET)
    stage.push_command(setter_node_command)
    setter_node: SetterNode = setter_node_command.result_node
    setter_node["value"].push_value("test")

    getter_node_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.GET)
    stage.push_command(getter_node_command)
    getter_node: GetterNode = getter_node_command.result_node

    getter_node["node_path"].push_value(log_node.path.as_posix())
    getter_node["cpnt_name"].push_value("message")

    link_getter_command = commands.LinkNodeComponentsCommand(
        stage=stage, source=getter_node["value"], target=setter_node["value"]
    )
    stage.push_command(link_getter_command)
    stage.export_json(export_path)

    assert setter_node["value"].raw_value != log_node["message"].raw_value
    assert setter_node["value"].pull_value() == log_node["message"].cached_value
