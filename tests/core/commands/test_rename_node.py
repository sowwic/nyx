import pytest

from nyx.core.commands import CreateNodeCommand, RenameNodeCommand
from nyx.core.exceptions import NyxCommandValidationError, StageObjectQueryError
from nyx.core.stage import Stage


def test_rename_single_top_node():
    """Test simple rename of single top level node"""
    stage = Stage()
    original_path = stage.root_node.path / "test_node"
    new_path = original_path.with_name("new_name")

    create_node_command = CreateNodeCommand(stage=stage, name=original_path.name)
    stage.push_command(create_node_command)
    node = stage.get_object(original_path)

    rename_command = RenameNodeCommand(stage, node=node, new_name="new_name")
    stage.push_command(rename_command)

    with pytest.raises(StageObjectQueryError):
        stage.get_object(original_path)
    assert stage.get_object(new_path) is not None

    node = stage.get_object(new_path)
    assert node.name == new_path.name
    assert node.path == new_path


def test_rename_undo_redo() -> None:
    """Test rename undo-redo."""
    stage = Stage()
    original_path = stage.root_node.path / "test_node"
    new_path = original_path.with_name("new_name")

    create_node_command = CreateNodeCommand(stage=stage, name=original_path.name)
    stage.push_command(create_node_command)
    node = stage.get_object(original_path)

    rename_command = RenameNodeCommand(stage, node=node, new_name="new_name")
    stage.push_command(rename_command)

    stage.undo_stack.undo()
    assert stage.get_object(original_path) is not None

    with pytest.raises(StageObjectQueryError):
        stage.get_object(new_path)

    stage.undo_stack.redo()
    with pytest.raises(StageObjectQueryError):
        stage.get_object(original_path)
    assert stage.get_object(new_path) is not None


def test_rename_non_existent_node_raises_validation_error():
    """Test renaming of non existent node failing."""
    stage = Stage()
    original_name = "test_node"

    rename_command = RenameNodeCommand(
        stage, node=f"/{original_name}", new_name="new_name"
    )
    with pytest.raises(NyxCommandValidationError):
        stage.push_command(rename_command)


def test_child_node_path_is_correct_after_renaming() -> None:
    """Test child node path after parent renaming."""

    stage = Stage()
    parent_path = stage / "parent_node"
    new_parent_path = parent_path.with_name("new_node")
    expected_child_path = new_parent_path / "child_node"

    parent_command = CreateNodeCommand(stage=stage, name=parent_path.name)
    stage.push_command(parent_command)

    child_command = CreateNodeCommand(
        stage=stage, parent_node=parent_path, name=expected_child_path.name
    )
    stage.push_command(child_command)

    rename_command = RenameNodeCommand(
        stage, node=parent_path, new_name=new_parent_path.name
    )
    stage.push_command(rename_command)

    child_node = stage.get_object(expected_child_path)
    assert child_node is not None
    assert child_node.path == expected_child_path
