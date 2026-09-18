import typing
from nyx.api.v1 import Stage, CoreNodes, CoreNodeComponents, commands

if typing.TYPE_CHECKING:
    from nyx.plugins.core.nodes.branch import BranchNode


def test_branch_node_creation():
    """Test creating new branch node with default parameters."""
    stage = Stage()
    command = commands.CreateNodeCommand(stage=stage, node_type_id=CoreNodes.BRANCH)
    stage.push_command(command)
    result_node: BranchNode = stage.node(command.node_path)

    assert result_node is not None
    assert result_node.get_type_id() == CoreNodes.BRANCH
    assert (
        next(
            result_node.components_model.find_components_of_type(CoreNodeComponents.FLOW)
        )
        is not None
    )
    assert (
        next(
            result_node.components_model.find_components_of_type(
                CoreNodeComponents.VALUE
            )
        )
        is not None
    )


def test_execute_activates_correct_flow_out():
    stage = Stage()
    command = commands.CreateNodeCommand(stage=stage, node_type_id="core:branch")
    stage.push_command(command)
    branch_node = stage.node(command.node_path)
    assert branch_node is not None

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
