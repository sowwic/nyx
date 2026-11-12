import typing
from nyx.api.v1 import Stage, NodeComponent, CoreNodes, CoreNodeComponents, commands

if typing.TYPE_CHECKING:
    from nyx.stdlib.nodes.log import LogNode


def test_log_node_creation():
    """Test creating new log node with default parameters."""
    stage = Stage()
    command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.LOG)
    stage.push_command(command)
    result_node: LogNode | None = stage.get_object(command.result_node.uuid)

    assert result_node is not None
    assert result_node.get_type_id() == CoreNodes.LOG
    assert (
        next(
            result_node.components_model.find_components_of_type(CoreNodeComponents.FLOW)
        )
        is not None
    )
    assert result_node._logger is None
    message_cpnt = result_node.components_model.get_component("message")
    assert message_cpnt is not None
    assert message_cpnt.get_type_id() == CoreNodeComponents.VALUE
    assert message_cpnt.pull_value() == ""

    level_cpnt = result_node.components_model.get_component("level")
    assert level_cpnt is not None
    assert level_cpnt.get_type_id() == CoreNodeComponents.VALUE
    assert level_cpnt.pull_value() == result_node.DEFAULT_LEVEL


def test_execute_components_creates_logger_with_expected_name():
    """Check logger post components execution"""
    stage = Stage()
    command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.LOG)
    stage.push_command(command)
    log_node: LogNode = stage.get_object(command.result_node)
    log_node["message"].push_value("test_message")
    log_node.execute_components()

    assert log_node.logger is not None


def test_message_is_a_string_and_level_an_int():
    from nyx.api.v1 import CoreDatatypes

    stage = Stage()
    command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.LOG)
    stage.push_command(command)
    log_node: LogNode = stage.get_object(command.result_node)

    log_node["message"].push_value("123")
    log_node["level"].push_value("20")

    assert log_node["message"].datatype_id == CoreDatatypes.STRING
    assert log_node["message"].cached_value == "123"
    assert log_node["level"].datatype_id == CoreDatatypes.INT
    assert log_node["level"].cached_value == 20


def test_invalid_level_is_flagged_and_keeps_previous_value():
    stage = Stage()
    command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.LOG)
    stage.push_command(command)
    level: NodeComponent = stage.get_object(command.result_node)["level"]

    level.push_value("loud")

    assert not level.is_valid
    assert level.cached_value == level.default_value
