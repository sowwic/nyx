from nyx.api.v1 import Stage
from nyx.api.v1 import commands


def test_branch_node_creation():
    """Test creating new branch node with default parameters."""
    stage = Stage()
    command = commands.CreateNodeCommand(stage=stage, node_type_id="core:branch")
    stage.push_command(command)
    expected_path = stage.ROOT_NODE_PATH / "node"
    result_node = stage.node(expected_path)

    assert result_node is not None
    assert result_node.TYPE_ID == "core:branch"
    assert (
        next(result_node.components_model.find_components_of_type("core:flow"))
        is not None
    )
    assert (
        next(result_node.components_model.find_components_of_type("core:value"))
        is not None
    )


def test_execute_activates_correct_flow_out():
    stage = Stage()
    command = commands.CreateNodeCommand(stage=stage, node_type_id="core:branch")
    stage.push_command(command)
    branch_node = stage.node(command.node_path)

    # True case
    branch_node["value"].value = True
    branch_node.execute()

    assert branch_node["flow_in"].is_active is True
    assert branch_node["flow_out_true"].is_active is True
    assert branch_node["flow_out_false"].is_active is False
    # Switch to false
    branch_node["value"].value = False
    branch_node.execute()

    assert branch_node["flow_in"].is_active is True
    assert branch_node["flow_out_true"].is_active is False
    assert branch_node["flow_out_false"].is_active is True
