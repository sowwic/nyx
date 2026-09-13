from nyx.api.v1 import Stage
from nyx.api.v1 import commands
from nyx.api.v1 import test_helpers


@test_helpers.with_plugins("NyxCore")
def test_branch_node_creation():
    """Test creating new branch node with default parameters."""
    stage = Stage()
    command = commands.CreateNodeCommand(stage=stage, node_type_id="core:branch")
    stage.push_command(command)
    expected_path = "/node"

    result_node = stage.node(expected_path)

    assert result_node is not None
    assert result_node.TYPE_ID == "branch"
    assert (
        next(result_node.components_model.find_components_of_type("core:flow"))
        is not None
    )
    assert (
        next(result_node.components_model.find_components_of_type("core:value"))
        is not None
    )
