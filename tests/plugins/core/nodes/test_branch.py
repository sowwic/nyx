from nyx.api.v1 import Stage
from nyx.api.v1 import commands
from nyx.api.v1 import test_helpers


@test_helpers.with_plugins("NyxCore")
def test_branch_node_creation():
    """Test creating new branch node with default parameters."""
    stage = Stage()
    command = commands.CreateNodeCommand(stage=stage, node_type_id="branch")
    stage.push_command(command)
    expected_path = "/node"

    result_node = stage.node(expected_path)

    assert result_node is not None
    assert result_node.TYPE_ID == "branch"
    assert len(result_node.components_model.list_components(type_id_filter="flow")) == 1
    assert len(result_node.components_model.list_components(type_id_filter="value")) == 1
