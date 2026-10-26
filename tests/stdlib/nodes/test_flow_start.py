import typing
from nyx.api.v1 import Stage, CoreNodeComponents, CoreNodes, commands

if typing.TYPE_CHECKING:
    from nyx.stdlib.nodes.flow_start import FlowStartNode


def test_flow_start_node_creation():
    """Test creating new FlowStart node with default parameters."""
    stage = Stage()
    command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.FLOW_START)
    stage.push_command(command)

    result_node: FlowStartNode = stage.get_object(command.result_node.uuid)

    assert result_node is not None
    assert result_node.get_type_id() == CoreNodes.FLOW_START
    assert (
        next(
            result_node.components_model.find_components_of_type(CoreNodeComponents.FLOW)
        )
        is not None
    )
