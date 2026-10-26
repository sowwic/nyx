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
    assert flow.writable is True
    assert flow.readable is True

    in_component_path = result_node["component"]
    assert in_component_path.get_type_id() == CoreNodeComponents.STAGE_OBJECT_PATH
    assert in_component_path.is_editable is True
    assert in_component_path.writable is True
    assert in_component_path.readable is False

    in_value = result_node["value"]
    assert in_value.get_type_id() == CoreNodeComponents.VALUE
    assert in_value.writable is True
    assert in_value.readable is False


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


def test_setter_value_datatype_is_unlocked_until_linked():
    from nyx.api.v1 import CoreDatatypes

    stage = Stage()
    log_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.LOG)
    stage.push_command(log_command)
    setter_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.SET)
    stage.push_command(setter_command)
    value = setter_command.result_node["value"]
    assert value.is_built_in
    assert not value.is_datatype_locked

    stage.push_command(
        commands.SetNodeComponentDatatypeCommand(
            stage=stage, node_component=value, datatype_id=CoreDatatypes.PATH
        )
    )
    assert value.datatype.type_id == CoreDatatypes.PATH

    source = log_command.result_node["level"]
    source.readable = True
    with pytest.raises(exceptions.NyxCommandValidationError, match="different datatype"):
        stage.push_command(
            commands.LinkNodeComponentsCommand(stage=stage, source=source, target=value)
        )


def test_setter_value_takes_the_datatype_of_the_linked_component():
    from nyx.api.v1 import CoreDatatypes

    stage = Stage()
    log_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.LOG)
    stage.push_command(log_command)
    setter_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.SET)
    stage.push_command(setter_command)
    value = setter_command.result_node["value"]
    source = log_command.result_node["message"]
    source.readable = True

    stage.push_command(
        commands.LinkNodeComponentsCommand(stage=stage, source=source, target=value)
    )

    assert value.datatype.type_id == CoreDatatypes.STRING
    assert value.is_datatype_locked

    stage.undo_stack.undo()
    assert value.datatype.type_id == CoreDatatypes.OBJECT
    assert not value.is_datatype_locked


def make_setter_and_log():
    stage = Stage()
    log_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.LOG)
    stage.push_command(log_command)
    setter_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.SET)
    stage.push_command(setter_command)
    log_node, setter_node = log_command.result_node, setter_command.result_node
    setter_node["component"].push_value(f"./{log_node.name}.level")
    return log_node, setter_node


def test_setter_casts_the_value_to_the_datatype_of_the_target():
    log_node, setter_node = make_setter_and_log()
    setter_node["value"].push_value("30")  # evaluated to 30 already

    setter_node.execute()
    assert log_node["level"].cached_value == 30

    setter_node["value"].push_value("'40'")  # a string, the target is an int
    setter_node.execute()
    assert log_node["level"].cached_value == 40
    assert log_node["level"].is_valid


def test_setter_raises_and_leaves_the_target_when_the_cast_fails():
    from nyx.core.exceptions import DatatypeCastError

    log_node, setter_node = make_setter_and_log()
    setter_node["value"].push_value("'loud'")

    with pytest.raises(DatatypeCastError):
        setter_node.execute()

    assert log_node["level"].cached_value == 10
    assert log_node["level"].is_valid


def test_setter_uses_the_datatype_default_for_a_missing_value():
    log_node, setter_node = make_setter_and_log()
    setter_node["value"].push_value(None)

    setter_node.execute()

    assert log_node["level"].cached_value == 0


def test_setter_title_follows_linked_value_node_path():
    stage = Stage()
    log_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.LOG)
    stage.push_command(log_command)
    value_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.VALUE)
    stage.push_command(value_command)
    setter_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.SET)
    stage.push_command(setter_command)
    log_node = log_command.result_node
    value_node = value_command.result_node
    setter_node: SetterNode = setter_command.result_node

    value_node["value"].push_value(f"{log_node.path}.message")
    stage.push_command(
        commands.LinkNodeComponentsCommand(
            stage=stage, source=value_node["value"], target=setter_node["component"]
        )
    )

    assert setter_node["component"].resolve_component() is log_node["message"]
    assert setter_node.subtitle == f"{log_node.name}.message"
    assert setter_node["component"].get_display_value() != f"{log_node.path}.message"
