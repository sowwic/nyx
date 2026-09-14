from nyx.api.v1 import Stage
from nyx.api.v1 import commands
from nyx.api.v1 import pytest_helpers


@pytest_helpers.with_plugins("NyxCore")
def test_flow_start_node_creation():
    """Test creating new FlowStart node with default parameters."""
    stage = Stage()
    command = commands.CreateNodeCommand(stage=stage, node_type_id="core:flow_start")
    stage.push_command(command)
    expected_path = stage.ROOT_NODE_PATH / "node"

    result_node = stage.node(expected_path)

    assert result_node is not None
    assert result_node.TYPE_ID == "flow_start"
    assert (
        next(result_node.components_model.find_components_of_type("core:flow"))
        is not None
    )
