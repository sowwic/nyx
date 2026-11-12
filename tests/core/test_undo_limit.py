import pytest
from pydantic import ValidationError

from nyx.api.v1 import CoreNodes, Stage, commands
from nyx.core.config_values import NyxConfigValues
from nyx.static.vars import DEFAULT_UNDO_LIMIT


def push_node(stage: Stage, name: str):
    stage.push_command(
        commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.EMPTY, name=name)
    )


def test_default_limit_is_the_configured_default():
    assert Stage().undo_limit == DEFAULT_UNDO_LIMIT
    assert NyxConfigValues().editor_behaviour.undo_limit == DEFAULT_UNDO_LIMIT


def test_the_oldest_commands_are_dropped_past_the_limit():
    stage = Stage(undo_limit=3)

    for index in range(5):
        push_node(stage, f"n{index}")

    assert stage.undo_stack.count() == 3
    while stage.undo_stack.canUndo():
        stage.undo_stack.undo()
    # The two oldest nodes can't be undone any more.
    assert [n.name for n in stage.list_children(stage.root_node)] == ["n0", "n1"]


def test_a_group_of_commands_counts_as_one_step():
    stage = Stage(undo_limit=2)

    stage.undo_stack.beginMacro("many")
    for index in range(4):
        push_node(stage, f"n{index}")
    stage.undo_stack.endMacro()

    assert stage.undo_stack.count() == 1


def test_zero_means_no_limit():
    stage = Stage(undo_limit=0)

    for index in range(10):
        push_node(stage, f"n{index}")

    assert stage.undo_stack.count() == 10


def test_the_limit_can_be_changed_while_the_history_is_empty():
    stage = Stage(undo_limit=10)

    stage.undo_limit = 2
    for index in range(4):
        push_node(stage, f"n{index}")

    assert stage.undo_limit == 2
    assert stage.undo_stack.count() == 2


def test_the_limit_is_kept_once_there_is_history(caplog):
    stage = Stage(undo_limit=10)
    push_node(stage, "a")

    with caplog.at_level("WARNING"):
        stage.undo_limit = 2

    assert stage.undo_limit == 10
    assert "undo limit" in caplog.text


def test_negative_limit_means_no_limit():
    stage = Stage()

    stage.undo_limit = -5

    assert stage.undo_limit == 0


def test_stage_is_modified_after_a_command_when_the_stack_is_full(tmp_path):
    stage = Stage(undo_limit=2)
    push_node(stage, "a")
    push_node(stage, "b")
    stage.export_json(tmp_path / f"stage{stage.FILE_EXTENSION}")
    assert not stage.is_modified()

    # The stack is full: the new command pushes the oldest out and leaves the
    # number of commands and the index unchanged.
    push_node(stage, "c")

    assert stage.is_modified()


def test_undoing_back_to_the_saved_state_is_not_modified(tmp_path):
    stage = Stage(undo_limit=5)
    push_node(stage, "a")
    stage.export_json(tmp_path / f"stage{stage.FILE_EXTENSION}")
    push_node(stage, "b")
    assert stage.is_modified()

    stage.undo_stack.undo()

    assert not stage.is_modified()


def test_stage_stays_modified_once_the_saved_state_was_dropped(tmp_path):
    stage = Stage(undo_limit=2)
    stage.export_json(tmp_path / f"stage{stage.FILE_EXTENSION}")
    for index in range(4):
        push_node(stage, f"n{index}")

    while stage.undo_stack.canUndo():
        stage.undo_stack.undo()

    # The oldest commands, back to the saved state, are gone.
    assert stage.is_modified()


def test_clearing_the_history_leaves_the_stage_modified(tmp_path):
    stage = Stage()
    stage.export_json(tmp_path / f"stage{stage.FILE_EXTENSION}")
    assert not stage.is_modified()

    stage.clear_undo_history()

    assert stage.is_modified()


def test_config_value_rejects_a_negative_limit():
    with pytest.raises(ValidationError):
        NyxConfigValues(editor_behaviour={"undo_limit": -1})
