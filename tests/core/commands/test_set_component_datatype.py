from nyx.api.v1 import Stage, CoreNodes, CoreDatatypes, commands


def make_condition(stage: Stage):
    command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.BRANCH)
    stage.push_command(command)
    return command.result_node["condition"]


def test_set_datatype_is_undoable():
    stage = Stage()
    condition = make_condition(stage)
    condition.push_value("5")

    stage.push_command(
        commands.SetNodeComponentDatatypeCommand(
            stage=stage, node_component=condition, datatype_id=CoreDatatypes.INT
        )
    )
    assert condition.datatype_id == CoreDatatypes.INT
    assert condition.cached_value == 5

    stage.undo_stack.undo()
    assert condition.datatype_id == CoreDatatypes.BOOL
    assert condition.cached_value is True

    stage.undo_stack.redo()
    assert condition.datatype_id == CoreDatatypes.INT
