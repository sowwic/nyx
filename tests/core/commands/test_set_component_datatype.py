import pytest

from nyx.api.v1 import Stage, CoreNodes, CoreNodeComponents, CoreDatatypes, commands
from nyx.core.exceptions import NyxCommandValidationError


def make_condition(stage: Stage):
    command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.BRANCH)
    stage.push_command(command)
    return command.result_node["condition"]


def make_user_value(stage: Stage):
    node_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.EMPTY)
    stage.push_command(node_command)
    add = commands.AddNodeComponentCommand(
        node=node_command.result_node, type_id=CoreNodeComponents.VALUE
    )
    stage.push_command(add)
    return add.result_component


def test_set_datatype_is_undoable():
    stage = Stage()
    value = make_user_value(stage)
    value.push_value("5")

    stage.push_command(
        commands.SetNodeComponentDatatypeCommand(
            stage=stage, node_component=value, datatype_id=CoreDatatypes.STRING
        )
    )
    assert value.datatype_id == CoreDatatypes.STRING
    assert value.cached_value == "5"

    stage.undo_stack.undo()
    assert value.datatype_id == CoreDatatypes.OBJECT
    assert value.cached_value == 5

    stage.undo_stack.redo()
    assert value.datatype_id == CoreDatatypes.STRING


def test_built_in_component_datatype_is_locked():
    stage = Stage()
    condition = make_condition(stage)
    assert condition.is_built_in
    assert condition.is_datatype_locked

    with pytest.raises(NyxCommandValidationError, match="locked"):
        stage.push_command(
            commands.SetNodeComponentDatatypeCommand(
                stage=stage, node_component=condition, datatype_id=CoreDatatypes.INT
            )
        )
    assert condition.datatype_id == CoreDatatypes.BOOL
