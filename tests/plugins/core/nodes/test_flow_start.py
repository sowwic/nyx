from nyx.api.v1 import Stage, CoreNodeComponents, CoreNodes, commands


def test_flow_start_node_creation():
    """Test creating new FlowStart node with default parameters."""
    stage = Stage()
    command = commands.CreateNodeCommand(stage=stage, node_type_id=CoreNodes.FLOW_START)
    stage.push_command(command)

    result_node = stage.node(command.node_path)

    assert result_node is not None
    assert result_node.TYPE_ID == CoreNodes.FLOW_START
    assert (
        next(
            result_node.components_model.find_components_of_type(CoreNodeComponents.FLOW)
        )
        is not None
    )
