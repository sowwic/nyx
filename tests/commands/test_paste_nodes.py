from PySide6 import QtCore

from nyx.core.commands import CreateNodeCommand, PasteNodesCommand
from nyx.core.stage import Stage
from nyx.editor.utils import clipboard


def test_paste_node_to_other_stage(nyx_app) -> None:
    """Test copy-pasting nodes between stages.

    Args:
        nyx_app (NyxApplication): application fixture
    """
    stage1 = Stage()
    command = CreateNodeCommand(stage=stage1)
    stage1.push_command(command)

    node = stage1.node("/node")
    nodes_to_copy = [node]
    clipboard.serialize_nodes_to_clipboard(nodes=nodes_to_copy, delete=False)

    stage2 = Stage()
    clipboard_data = clipboard.get_serialized_nodes_from_clipboard()
    paste_position = QtCore.QPointF(10.0, 10.0)
    paste_command = PasteNodesCommand(
        stage=stage2, serialize_nodes=clipboard_data, position=paste_position
    )
    stage2.push_command(paste_command)

    assert stage2.total_node_count() == 1
    assert stage2.node("/node") is not None
    pasted_node = stage2.node("/node")
    assert pasted_node.position() == paste_position


def test_paste_undo_redo(nyx_app) -> None:
    """Test paste nodes undo redo

    Args:
        nyx_app (NyxApplication): application fixture
    """
    stage = Stage()
    command = CreateNodeCommand(stage=stage)
    stage.push_command(command)

    node = stage.node("/node")
    nodes_to_copy = [node]
    clipboard.serialize_nodes_to_clipboard(nodes=nodes_to_copy, delete=False)

    clipboard_data = clipboard.get_serialized_nodes_from_clipboard()
    paste_position = QtCore.QPointF(10.0, 10.0)
    paste_command = PasteNodesCommand(
        stage=stage, serialize_nodes=clipboard_data, position=paste_position
    )
    stage.push_command(paste_command)

    assert stage.node("/node1") is not None
    stage.undo_stack.undo()
    assert stage.node("/node1") is None
    stage.undo_stack.redo()
    assert stage.node("/node1") is not None


def test_paste_parent_filter(nyx_app):
    """Test multiple nodes from clipboard where one of them is child of another.

    Args:
        nyx_app (NyxApplication): application fixture
    """
    stage1 = Stage()

    create_command1 = CreateNodeCommand(stage=stage1, node_name="node1")
    create_command2 = CreateNodeCommand(
        stage=stage1, node_name="node2", parent_path="/node1"
    )
    stage1.push_command(create_command1)
    stage1.push_command(create_command2)
    node1 = stage1.node("/node1")
    node2 = stage1.node("/node1/node2")

    nodes_to_copy = [node1, node2]
    clipboard.serialize_nodes_to_clipboard(nodes=nodes_to_copy, delete=False)

    stage2 = Stage()
    create_command3 = CreateNodeCommand(stage=stage2, node_name="parent_node")
    stage2.push_command(create_command3)

    clipboard_data = clipboard.get_serialized_nodes_from_clipboard()
    paste_position = QtCore.QPointF(10.0, 10.0)

    paste_command_filter_check = PasteNodesCommand(
        stage=stage2, serialize_nodes=clipboard_data, position=paste_position
    )
    paste_command_filter_check.filter_serialized_nodes()

    assert len(paste_command_filter_check.serialized_nodes) == 1

    paste_command = PasteNodesCommand(
        stage=stage2,
        serialize_nodes=clipboard_data,
        position=paste_position,
        parent_node="/parent_node",
    )

    stage2.push_command(paste_command)
    assert stage2.node("/parent_node/node1") is not None
    assert stage2.node("/parent_node/node1/node2") is not None
    assert stage2.total_node_count() == 3
