import pathlib
import logging

import pytest

from nyx.api.v1 import Stage, CoreNodes, commands

LOGGER = logging.getLogger(__name__)


def test_crawler_order_correct_with_flat_hierarchy():
    stage = Stage()

    flow_create_command = commands.CreateNodeCommand(
        stage=stage, node_type_id=CoreNodes.FLOW_START
    )
    action1_create_command = commands.CreateNodeCommand(
        stage=stage, node_type_id=CoreNodes.ACTION
    )
    action2_create_command = commands.CreateNodeCommand(
        stage=stage, node_type_id=CoreNodes.ACTION
    )
    stage.push_command(flow_create_command)
    stage.push_command(action1_create_command)
    stage.push_command(action2_create_command)

    flow_create_command.result_node["flow"].value = action1_create_command.node_path
    action1_create_command.result_node["flow"].value = action2_create_command.node_path

    stage.crawler.start()
    assert stage.crawler.visited_node_paths == [
        stage.ROOT_NODE_PATH.as_posix(),
        flow_create_command.node_path,
        action1_create_command.node_path,
        action2_create_command.node_path,
    ]


def test_crawler_order_correct_with_nested_hierarchy(
    output_dir: pathlib.Path, request: pytest.FixtureRequest
):
    """
    Check that crawler visits nested nodes hierarchy in the correct order.

    Stage hierarchy:
    - flow_start
    - action1
        - flow_start
        - child_action
    - action2
        - flow_start
        - child_action

    Flow Connections:
    flow_start -> action1 -> action2

    Nested nodes flow connections:
    flow_start -> child_action

    Expected order:
        > flow_start
        > action1/flow_start
        > action1/child_action
        > action1
        > action2/flow_start
        > action2/child_action
        > action2
    """
    # Setup stage and top level nodes
    stage = Stage()
    export_path = output_dir / f"{request.node.name}{stage.FILE_EXTENSION}"
    flow_create_command = commands.CreateNodeCommand(
        stage=stage, node_type_id=CoreNodes.FLOW_START
    )
    action1_create_command = commands.CreateNodeCommand(
        stage=stage, node_type_id=CoreNodes.LOG
    )
    action2_create_command = commands.CreateNodeCommand(
        stage=stage, node_type_id=CoreNodes.LOG
    )

    stage.push_command(flow_create_command)
    stage.push_command(action1_create_command)
    stage.push_command(action2_create_command)

    root_flow_start_node = stage.node(flow_create_command.node_path)
    action1_node = stage.node(action1_create_command.node_path)
    action2_node = stage.node(action2_create_command.node_path)

    # Setup children of action1
    flow_node1_create_command = commands.CreateNodeCommand(
        stage=stage,
        node_type_id=CoreNodes.FLOW_START,
        parent_path=action1_node.path,
    )
    child_node1_create_command = commands.CreateNodeCommand(
        stage=stage,
        node_type_id=CoreNodes.LOG,
        parent_path=action1_node.path,
    )
    stage.push_command(flow_node1_create_command)
    stage.push_command(child_node1_create_command)

    action1_flow_start = action1_node.find_flow_start_node()
    action1_child = stage.node(child_node1_create_command.node_path)

    # # Setup children of action2
    flow_node2_create_command = commands.CreateNodeCommand(
        stage=stage,
        node_type_id=CoreNodes.FLOW_START,
        parent_path=action2_node.path,
    )
    child_node2_create_command = commands.CreateNodeCommand(
        stage=stage,
        node_type_id=CoreNodes.LOG,
        parent_path=action2_node.path,
    )
    stage.push_command(flow_node2_create_command)
    stage.push_command(child_node2_create_command)

    action2_flow_start = action2_node.find_flow_start_node()
    action2_child = stage.node(child_node2_create_command.node_path)

    # Setup flow connections
    root_flow_start_node["flow"].value = action1_node.path
    action1_node["flow"].value = action2_node.path

    action1_flow_start["flow"].value = action1_child.path
    action2_flow_start["flow"].value = action2_child.path

    # Setup messages
    action1_node["message"].value = "ACTION1"
    action2_node["message"].value = "ACTION2"
    action1_child["message"].value = "ACTION1_CHILD"
    action2_child["message"].value = "ACTION2_CHILD"

    # Perform stage crawl
    stage.crawler.start()
    stage.export_json(export_path)
    assert stage.crawler.visited_node_paths == [
        stage.ROOT_NODE_PATH.as_posix(),
        root_flow_start_node.path.as_posix(),
        action1_node.path.as_posix(),
        action1_flow_start.path.as_posix(),
        action1_child.path.as_posix(),
        action2_node.path.as_posix(),
        action2_flow_start.path.as_posix(),
        action2_child.path.as_posix(),
    ]
    assert stage.crawler._execution_paths_stack == [
        root_flow_start_node.path.as_posix(),
        action1_flow_start.path.as_posix(),
        action1_child.path.as_posix(),
        action1_node.path.as_posix(),
        action2_flow_start.path.as_posix(),
        action2_child.path.as_posix(),
        action2_node.path.as_posix(),
        stage.ROOT_NODE_PATH.as_posix(),
    ]
