import pytest

from nyx.core.commands import CreateNodeCommand, SetNodeActiveStateCommand
from nyx.core.exceptions import NyxCommandValidationError
from nyx.api.v1 import Stage


def test_active_stage_change() -> None:
    """Test command setting node state"""
    stage = Stage()
    command = CreateNodeCommand(stage=stage)
    stage.push_command(command)

    node = stage.get_object(command.result_node.uuid)
    state_set_false_command = SetNodeActiveStateCommand(
        stage=stage, node=command.result_node, state=False
    )
    state_set_true_command = SetNodeActiveStateCommand(
        stage=stage, node=command.result_node.uuid, state=True
    )
    stage.push_command(state_set_false_command)

    assert node.is_active() is False
    stage.push_command(state_set_true_command)
    assert node.is_active() is True


def test_active_set_undo_redo() -> None:
    """Test command setting node state undo-redo"""
    stage = Stage()
    test_node_path = stage / "node"

    command = CreateNodeCommand(stage=stage)
    stage.push_command(command)

    node = stage.get_object(test_node_path)
    default_state = node.is_active()

    toggle_active_state_command = SetNodeActiveStateCommand(
        stage=stage, node=test_node_path, state=not default_state
    )
    stage.push_command(toggle_active_state_command)

    stage.undo_stack.undo()
    assert node.is_active() == default_state
    stage.undo_stack.redo()
    assert not node.is_active() == default_state


def test_non_existent_node_raises_validation_error() -> None:
    """Test command raising validation error for non existent node."""
    stage = Stage()
    state_set_false_command = SetNodeActiveStateCommand(
        stage=stage, node="/node", state=False
    )
    with pytest.raises(NyxCommandValidationError):
        stage.push_command(state_set_false_command)
