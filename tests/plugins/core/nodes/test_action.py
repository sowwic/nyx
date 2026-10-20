import typing
from nyx.api.v1 import Stage, CoreNodeComponents, CoreNodes, commands

if typing.TYPE_CHECKING:
    from nyx.plugins.core.nodes.action import ActionNode


def test_action_node_creation():
    """Test creating new Action node with default parameters."""
    stage = Stage()
    command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.ACTION)
    stage.push_command(command)

    result_node: ActionNode = stage.get_object(command.result_node.uuid)

    assert result_node is not None
    assert result_node.get_type_id() == CoreNodes.ACTION

    flow_components = list(
        result_node.components_model.find_components_of_type(CoreNodeComponents.FLOW)
    )
    assert len(flow_components) == 1
    assert flow_components[0].readable is True
    assert flow_components[0].writable is True
    assert flow_components[0].is_editable is False
