import pytest

from nyx.core.commands import CreateNodeCommand, RenameNodeCommand
from nyx.core.exceptions import NyxCommandValidationError
from nyx.core.stage import Stage


def test_rename_single_top_node():
    """Test simple rename of single top level node"""
    stage = Stage()
    original_name = "test_node"
    new_name = "new_name"

    create_parent_command = CreateNodeCommand(stage=stage, node_name=original_name)
    stage.push_command(create_parent_command)
    node = stage.node(f"/{original_name}")

    rename_command = RenameNodeCommand(stage, node=node, new_name="new_name")
    stage.push_command(rename_command)
    assert stage.node(f"/{original_name}") is None
    assert stage.node(f"/{new_name}") is not None

    node = stage.node(f"/{new_name}")
    assert node.path.as_posix() == f"/{new_name}"
    assert node.cached_path == node.path
    assert stage.path_map.get(node.path) is node


def test_rename_undo_redo() -> None:
    """Test rename undo-redo."""
    stage = Stage()
    original_name = "test_node"
    new_name = "new_name"

    create_parent_command = CreateNodeCommand(stage=stage, node_name=original_name)
    stage.push_command(create_parent_command)
    node = stage.node(f"/{original_name}")

    rename_command = RenameNodeCommand(stage, node=node, new_name="new_name")
    stage.push_command(rename_command)

    stage.undo_stack.undo()
    assert stage.node(f"/{original_name}") is not None
    assert stage.node(f"/{new_name}") is None

    stage.undo_stack.redo()
    assert stage.node(f"/{original_name}") is None
    assert stage.node(f"/{new_name}") is not None


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
    expected_child_path = "/new_node/child_node"

    stage = Stage()
    parent_command = CreateNodeCommand(stage=stage, node_name="parent_node")
    stage.push_command(parent_command)

    child_command = CreateNodeCommand(
        stage=stage, parent_path="/parent_node", node_name="child_node"
    )
    stage.push_command(child_command)

    rename_command = RenameNodeCommand(stage, node="/parent_node", new_name="new_node")
    stage.push_command(rename_command)

    child_node = stage.node(expected_child_path)
    assert child_node is not None
    assert (
        child_node.path.as_posix()
        == child_node.cached_path.as_posix()
        == expected_child_path
    )
