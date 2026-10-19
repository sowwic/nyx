import pathlib
import pytest
import typing
from nyx.api.v1 import Stage, CoreNodes, CoreNodeComponents, commands, exceptions

if typing.TYPE_CHECKING:
    from nyx.plugins.core.nodes.getter import GetterNode
    from nyx.plugins.core.nodes.setter import SetterNode


def test_getter_creation():
    """Test creating new log node with default parameters."""
    stage = Stage()
    command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.GET)
    stage.push_command(command)
    result_node: GetterNode = stage.get_object(command.result_node.uuid)

    assert result_node.components_model.rowCount() == 2

    in_component_path = result_node["component"]
    assert in_component_path.get_type_id() == CoreNodeComponents.STAGE_REFERENCE
    assert in_component_path.is_editable is True
    assert in_component_path.accepts_input is False
    assert in_component_path.produces_output is False

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

    getter_node["component"].push_value(f"{log_node.path.as_posix()}.message")

    link_getter_command = commands.LinkNodeComponentsCommand(
        stage=stage, source=getter_node["value"], target=setter_node["value"]
    )
    stage.push_command(link_getter_command)
    stage.export_json(export_path)

    assert setter_node["value"].raw_value != log_node["message"].raw_value
    assert setter_node["value"].pull_value() == log_node["message"].cached_value


def test_getter_display_value_is_empty_until_component_is_found():
    stage = Stage()
    target_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.LOG)
    stage.push_command(target_command)
    getter_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.GET)
    stage.push_command(getter_command)
    getter = getter_command.result_node
    target = target_command.result_node

    assert getter["value"].get_display_value() == ""  # no path yet
    getter["component"].push_value(target.path.as_posix())  # a node, not a component
    assert getter["value"].get_display_value() == ""
    getter["component"].push_value(f"{target.path.as_posix()}.message")
    assert getter["value"].get_display_value() == target["message"].get_display_value()


def test_getter_follows_renamed_node_and_component():
    stage = Stage()
    target_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.LOG)
    stage.push_command(target_command)
    getter_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.GET)
    stage.push_command(getter_command)
    target, getter = target_command.result_node, getter_command.result_node
    target["message"].push_value("hello")
    getter["component"].push_value(f"{target.path.as_posix()}.message")
    assert getter["value"].pull_value() == "hello"

    target.rename("renamed")
    target["message"].name = "text"
    assert getter["value"].pull_value() == "hello"
    assert getter["component"].pull_value() == f"{target.path.as_posix()}.text"


def test_getter_value_raises_for_missing_component():
    stage = Stage()
    getter_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.GET)
    stage.push_command(getter_command)
    getter = getter_command.result_node

    getter["component"].push_value("/stage/missing.value")
    with pytest.raises(exceptions.StageObjectQueryError):
        getter["value"].pull_value()
