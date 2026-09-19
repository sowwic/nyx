import pytest

from nyx.core.commands import CreateNodeCommand, RenameNodeCommand
from nyx.core.exceptions import NyxCommandValidationError
from nyx.core.stage import Stage


def test_rename_single_top_node():
    """Test simple rename of single top level node"""
    stage = Stage()
    original_path = stage.root_node.path / "test_node"
    new_path = original_path.with_name("new_name")

    create_node_command = CreateNodeCommand(stage=stage, node_name=original_path.name)
    stage.push_command(create_node_command)
    node = stage.node(original_path)

    rename_command = RenameNodeCommand(stage, node=node, new_name="new_name")
    stage.push_command(rename_command)
    assert stage.node(original_path) is None
    assert stage.node(new_path) is not None

    node = stage.node(new_path)
    assert node.path == new_path
    assert node.cached_path == node.path
    assert stage.path_map.get(node.path) is node


def test_rename_undo_redo() -> None:
    """Test rename undo-redo."""
    stage = Stage()
    original_path = stage.root_node.path / "test_node"
    new_path = original_path.with_name("new_name")

    create_node_command = CreateNodeCommand(stage=stage, node_name=original_path.name)
    stage.push_command(create_node_command)
    node = stage.node(original_path)

    rename_command = RenameNodeCommand(stage, node=node, new_name="new_name")
    stage.push_command(rename_command)

    stage.undo_stack.undo()
    assert stage.node(original_path) is not None
    assert stage.node(new_path) is None

    stage.undo_stack.redo()
    assert stage.node(original_path) is None
    assert stage.node(new_path) is not None


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

    parent_command = CreateNodeCommand(stage=stage, node_name=parent_path.name)
    stage.push_command(parent_command)

    child_command = CreateNodeCommand(
        stage=stage, parent_path=parent_path, node_name=expected_child_path.name
    )
    stage.push_command(child_command)

    rename_command = RenameNodeCommand(
        stage, node=parent_path, new_name=new_parent_path.name
    )
    stage.push_command(rename_command)

    child_node = stage.node(expected_child_path)
    assert child_node is not None
    assert child_node.path == child_node.cached_path == expected_child_path
