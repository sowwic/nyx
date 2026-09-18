import typing
from nyx.api.v1 import Stage, CoreNodes, CoreNodeComponents, commands

if typing.TYPE_CHECKING:
    from nyx.plugins.core.nodes.log import LogNode


def test_log_node_creation():
    """Test creating new log node with default parameters."""
    stage = Stage()
    command = commands.CreateNodeCommand(stage=stage, node_type_id=CoreNodes.LOG)
    stage.push_command(command)
    result_node: LogNode | None = stage.node(command.node_path)

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
    assert message_cpnt.value == ""

    level_cpnt = result_node.components_model.get_component("level")
    assert level_cpnt is not None
    assert level_cpnt.get_type_id() == CoreNodeComponents.VALUE
    assert level_cpnt.value == 10


def test_execute_components_creates_logger_with_expected_name():
    """Check logger post components execution"""
    stage = Stage()
    command = commands.CreateNodeCommand(stage=stage, node_type_id=CoreNodes.LOG)
    stage.push_command(command)
    log_node: LogNode = stage.node(command.node_path)
    log_node.message = "test_message"
    log_node.execute_components()

    assert log_node.logger is not None
    assert log_node.logger.name == log_node._compose_logger_name()
