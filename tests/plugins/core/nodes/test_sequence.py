import typing
from nyx.api.v1 import Stage, CoreNodeComponents, CoreNodes, commands

if typing.TYPE_CHECKING:
    from nyx.plugins.core.nodes.sequence import SequenceNode


def test_sequence_node_creation():
    """Test creating new Action node with default parameters."""
    stage = Stage()
    command = commands.CreateNodeCommand(stage=stage, node_type_id=CoreNodes.SEQUENCE)
    stage.push_command(command)

    result_node: SequenceNode = stage.node(command.node_path)

    assert result_node is not None
    assert result_node.TYPE_ID == CoreNodes.SEQUENCE

    flow_components = list(
        result_node.components_model.find_components_of_type(CoreNodeComponents.FLOW)
    )
    assert len(flow_components) == result_node.DEFAULT_OUTPUTS_COUNT
    assert flow_components[0].is_readable is True
    assert flow_components[0].is_writable is True
