import typing
from nyx.api.v1 import Stage, CoreNodes, CoreNodeComponents, commands

if typing.TYPE_CHECKING:
    from nyx.stdlib.nodes.branch import BranchNode


def test_branch_node_creation():
    """Test creating new branch node with default parameters."""
    stage = Stage()
    command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.BRANCH)
    stage.push_command(command)
    result_node: BranchNode = stage.get_object(command.result_node.uuid)

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
    command = commands.CreateNodeCommand(stage=stage, type_id="core:branch")
    stage.push_command(command)
    branch_node: BranchNode = stage.get_object(command.result_node.uuid)
    assert branch_node is not None

    # True case
    branch_node["condition"].push_value(True)
    branch_node.execution_hook()

    assert branch_node["flow"].is_active is True
    assert branch_node["true"].is_active is True
    assert branch_node["false"].is_active is False
    # Switch to false
    branch_node["condition"].push_value(False)
    branch_node.execution_hook()

    assert branch_node["flow"].is_active is True
    assert branch_node["true"].is_active is False
    assert branch_node["false"].is_active is True


def test_condition_is_hinted_as_bool():
    from nyx.api.v1 import CoreDatatypes

    stage = Stage()
    command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.BRANCH)
    stage.push_command(command)
    condition = command.result_node["condition"]

    condition.push_value("0")
    assert condition.datatype_id == CoreDatatypes.BOOL
    assert condition.cached_value is False


def test_branch_evaluates_when_condition_is_edited_or_linked():
    stage = Stage()
    branch_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.BRANCH)
    stage.push_command(branch_command)
    value_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.VALUE)
    stage.push_command(value_command)
    branch = branch_command.result_node
    value_node = value_command.result_node
    assert branch["true"].is_active

    stage.push_command(
        commands.SetNodeComponentValueCommand(
            stage=stage, node_component=branch["condition"], value="False"
        )
    )
    assert not branch["true"].is_active
    assert branch["false"].is_active

    value_node["value"].push_value("True")
    stage.push_command(
        commands.LinkNodeComponentsCommand(
            stage=stage, source=value_node["value"], target=branch["condition"]
        )
    )
    assert branch["true"].is_active
    assert not branch["false"].is_active


def test_branch_evaluates_when_linked_value_changes():
    stage = Stage()
    branch_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.BRANCH)
    stage.push_command(branch_command)
    value_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.VALUE)
    stage.push_command(value_command)
    branch = branch_command.result_node
    value_node = value_command.result_node
    stage.push_command(
        commands.LinkNodeComponentsCommand(
            stage=stage, source=value_node["value"], target=branch["condition"]
        )
    )

    stage.push_command(
        commands.SetNodeComponentValueCommand(
            stage=stage, node_component=value_node["value"], value="0"
        )
    )
    assert not branch["true"].is_active
    assert branch["false"].is_active

    stage.push_command(
        commands.SetNodeComponentValueCommand(
            stage=stage, node_component=value_node["value"], value="1"
        )
    )
    assert branch["true"].is_active
