import pytest
from PySide6 import QtCore

from nyx.editor.utils import clipboard
from nyx.api.v1 import CoreNodes, Stage, RestoreUuidOption, exceptions, commands


def test_paste_node_to_other_stage(nyx_app) -> None:
    """Test copy-pasting nodes between stages.

    Args:
        nyx_app (NyxApplication): application fixture
    """
    stage1 = Stage()
    test_type_id = CoreNodes.ACTION
    command = commands.CreateNodeCommand(stage=stage1, type_id=test_type_id)
    stage1.push_command(command)

    node = stage1.get_object(command.result_node.uuid)
    nodes_to_copy = [node]
    clipboard.serialize_nodes_to_clipboard(nodes=nodes_to_copy, delete=False)

    stage2 = Stage()
    clipboard_data = clipboard.get_serialized_nodes_from_clipboard()
    paste_position = QtCore.QPointF(10.0, 10.0)
    paste_command = commands.PasteNodesCommand(
        stage=stage2,
        serialize_nodes=clipboard_data,
        position=paste_position,
    )
    stage2.push_command(paste_command)

    assert stage2.total_node_count() == 1
    assert stage2.get_object(command.result_node.path) is not None
    assert stage2.get_object(command.result_node.path).get_type_id() == test_type_id

    pasted_node = stage2.get_object(command.result_node.path)
    assert pasted_node.position() == paste_position


def test_paste_undo_redo(nyx_app) -> None:
    """Test paste nodes undo redo

    Args:
        nyx_app (NyxApplication): application fixture
    """
    stage = Stage()
    test_node_path = stage.root_node.path / "node"
    pasted_node_path = stage.root_node.path / "node1"
    command = commands.CreateNodeCommand(stage=stage)
    stage.push_command(command)

    node = stage.get_object(test_node_path)
    nodes_to_copy = [node]
    clipboard.serialize_nodes_to_clipboard(nodes=nodes_to_copy, delete=False)

    clipboard_data = clipboard.get_serialized_nodes_from_clipboard()
    paste_position = QtCore.QPointF(10.0, 10.0)
    paste_command = commands.PasteNodesCommand(
        stage=stage, serialize_nodes=clipboard_data, position=paste_position
    )
    stage.push_command(paste_command)

    assert stage.total_node_count() == 2
    assert stage.get_object(pasted_node_path) is not None
    stage.undo_stack.undo()
    assert stage.total_node_count() == 1

    with pytest.raises(exceptions.StageObjectQueryError):
        assert stage.get_object(pasted_node_path) is None
    stage.undo_stack.redo()
    assert stage.total_node_count() == 2
    assert stage.get_object(pasted_node_path) is not None


def test_paste_parent_filter(nyx_app):
    """Test multiple nodes from clipboard where one of them is child of another.

    Args:
        nyx_app (NyxApplication): application fixture
    """
    stage1 = Stage()
    node1_path = stage1.root_node.path / "node1"
    node2_path = node1_path / "node2"

    create_command1 = commands.CreateNodeCommand(stage=stage1, name="node1")
    stage1.push_command(create_command1)

    create_command2 = commands.CreateNodeCommand(
        stage=stage1, name=node2_path.name, parent_node=node1_path
    )
    stage1.push_command(create_command2)

    node1 = stage1.get_object(node1_path)
    node2 = stage1.get_object(node2_path)

    nodes_to_copy = [node1, node2]
    clipboard.serialize_nodes_to_clipboard(nodes=nodes_to_copy, delete=False)

    stage2 = Stage()
    parent_node_path = stage2.root_node.path / "parent_node"
    create_command3 = commands.CreateNodeCommand(
        stage=stage2, name=parent_node_path.name
    )
    stage2.push_command(create_command3)

    clipboard_data = clipboard.get_serialized_nodes_from_clipboard()
    paste_position = QtCore.QPointF(10.0, 10.0)

    paste_command_filter_check = commands.PasteNodesCommand(
        stage=stage2, serialize_nodes=clipboard_data, position=paste_position
    )

    assert len(paste_command_filter_check.serialized_nodes) == 1

    paste_command = commands.PasteNodesCommand(
        stage=stage2,
        serialize_nodes=clipboard_data,
        position=paste_position,
        parent_node=parent_node_path,
    )

    stage2.push_command(paste_command)
    assert stage2.get_object(parent_node_path / node1_path.name) is not None
    assert (
        stage2.get_object(parent_node_path / node1_path.name / node2_path.name)
        is not None
    )
    assert stage2.total_node_count() == 3


def test_nested_chain_pasting_undo_redo():
    stage = Stage()
    node_command_1 = commands.CreateNodeCommand(stage=stage)
    stage.push_command(node_command_1)
    serialized_node_1 = node_command_1.result_node.serialize()

    paste_command_1 = commands.PasteNodesCommand(
        stage=stage,
        serialize_nodes=[serialized_node_1],
        position=QtCore.QPointF(),
        parent_node=node_command_1.result_node,
        restore_uuid=RestoreUuidOption.ATTEMPT_RESTORE,
    )
    stage.push_command(paste_command_1)

    paste_command_2 = commands.PasteNodesCommand(
        stage=stage,
        serialize_nodes=[serialized_node_1],
        position=QtCore.QPointF(),
        parent_node=stage.get_object(paste_command_1.created_uuids[0]),
        restore_uuid=RestoreUuidOption.ATTEMPT_RESTORE,
    )
    stage.push_command(paste_command_2)

    stage.undo_stack.undo()
    stage.undo_stack.undo()
    stage.undo_stack.undo()
    stage.undo_stack.redo()
    stage.undo_stack.redo()
    stage.undo_stack.redo()


def test_pasting_with_flat_links():
    stage = Stage()
    root_action1_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.ACTION
    )
    root_action2_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.ACTION
    )
    root_action3_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.ACTION
    )

    stage.push_command(root_action1_command, root_action2_command, root_action3_command)

    action1 = root_action1_command.result_node
    action2 = root_action2_command.result_node
    action3 = root_action3_command.result_node

    link1_command = commands.LinkNodeComponentsCommand(
        stage=stage, source=action1["flow"], target=action2["flow"]
    )
    link2_command = commands.LinkNodeComponentsCommand(
        stage=stage, source=action2["flow"], target=action3["flow"]
    )
    stage.push_command(link1_command, link2_command)

    assert action1["flow"].is_linked_to(action2["flow"], as_source=True)
    assert action2["flow"].is_linked_to(action3["flow"], as_source=True)

    serialized_action2 = action2.serialize()
    paste_command = commands.PasteNodesCommand(
        stage=stage,
        serialize_nodes=[serialized_action2],
        position=QtCore.QPointF(),
    )

    # Paste command
    stage.push_command(paste_command)
    pasted_action = paste_command.pasted_nodes[0]

    assert action1["flow"].is_linked_to(action2["flow"], as_source=True)
    assert action2["flow"].is_linked_to(action3["flow"], as_source=True)
    assert len(action2["flow"].input_links) == 1
    assert len(action3["flow"].input_links) == 1

    # The flow output of action1 is taken: the paste doesn't steal it.
    assert not action1["flow"].is_linked_to(pasted_action["flow"], as_source=True)
    assert len(pasted_action["flow"].links_uuids) == 0
    assert len(stage.collect_links()) == 2

    # Undo paste
    stage.undo_stack.undo()
    assert action1["flow"].is_linked_to(action2["flow"], as_source=True)
    assert action2["flow"].is_linked_to(action3["flow"], as_source=True)
    assert len(stage.collect_links()) == 2

    # Redo paste
    stage.undo_stack.undo()
    stage.undo_stack.redo()
    stage.undo_stack.redo()

    pasted_action = paste_command.pasted_nodes[0]

    assert action1["flow"].is_linked_to(action2["flow"], as_source=True)
    assert action2["flow"].is_linked_to(action3["flow"], as_source=True)
    assert len(action2["flow"].input_links) == 1
    assert len(action3["flow"].input_links) == 1

    # The flow output of action1 is taken: the paste doesn't steal it.
    assert not action1["flow"].is_linked_to(pasted_action["flow"], as_source=True)
    assert len(pasted_action["flow"].links_uuids) == 0
    assert len(stage.collect_links()) == 2


def test_paste_into_own_child():
    stage = Stage()

    main_node_command = commands.CreateNodeCommand(
        stage=stage, name="main", type_id=CoreNodes.ACTION
    )
    stage.push_command(main_node_command)

    main = main_node_command.result_node

    child_1_command = commands.CreateNodeCommand(
        stage=stage, name="child_one", type_id=CoreNodes.ACTION, parent_node=main
    )
    child_2_command = commands.CreateNodeCommand(
        stage=stage, name="child_two", type_id=CoreNodes.ACTION, parent_node=main
    )
    stage.push_command(child_1_command, child_2_command)

    child_one = child_1_command.result_node
    child_two = child_2_command.result_node

    link1_command = commands.LinkNodeComponentsCommand(
        stage=stage, source=child_one["flow"], target=child_two["flow"]
    )
    stage.push_command(link1_command)

    serialized_nodes = [child_one.serialize(), child_two.serialize()]

    paste_command = commands.PasteNodesCommand(
        stage=stage,
        serialize_nodes=serialized_nodes,
        position=QtCore.QPointF(),
        parent_node=main,
    )
    stage.push_command(paste_command)
    pasted_child1, pasted_child2 = paste_command.pasted_nodes
