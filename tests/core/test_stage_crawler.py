import pathlib
import logging

import pytest

from nyx.api.v1 import Stage, Node, CoreNodes, commands


LOGGER = logging.getLogger(__name__)


def test_crawler_order_correct_with_flat_hierarchy():
    stage = Stage()

    flow_create_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.FLOW_START
    )
    action1_create_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.ACTION
    )
    action2_create_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.ACTION
    )
    stage.push_command(flow_create_command)
    stage.push_command(action1_create_command)
    stage.push_command(action2_create_command)

    flow_create_command.result_node["flow"] >> action1_create_command.result_node["flow"]
    (
        action1_create_command.result_node["flow"]
        >> action2_create_command.result_node["flow"]
    )

    stage.crawler.start()
    assert stage.crawler.visited_node_paths == [
        stage.root_node.path.as_posix(),
        flow_create_command.result_node.path.as_posix(),
        action1_create_command.result_node.path.as_posix(),
        action2_create_command.result_node.path.as_posix(),
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
        stage=stage, type_id=CoreNodes.FLOW_START
    )
    action1_create_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.LOG
    )
    action2_create_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.LOG
    )

    stage.push_command(flow_create_command)
    stage.push_command(action1_create_command)
    stage.push_command(action2_create_command)

    root_flow_start_node = flow_create_command.result_node
    action1_node = action1_create_command.result_node
    action2_node = action2_create_command.result_node

    # Setup children of action1
    flow_node1_create_command = commands.CreateNodeCommand(
        stage=stage,
        type_id=CoreNodes.FLOW_START,
        parent_node=action1_node.path,
    )
    child_node1_create_command = commands.CreateNodeCommand(
        stage=stage,
        type_id=CoreNodes.LOG,
        parent_node=action1_node.path,
    )
    stage.push_command(flow_node1_create_command)
    stage.push_command(child_node1_create_command)

    action1_flow_start = action1_node.find_flow_start_node()
    action1_child: Node = stage.get_object(child_node1_create_command.result_node.uuid)

    # # Setup children of action2
    flow_node2_create_command = commands.CreateNodeCommand(
        stage=stage,
        type_id=CoreNodes.FLOW_START,
        parent_node=action2_node.path,
    )
    child_node2_create_command = commands.CreateNodeCommand(
        stage=stage,
        type_id=CoreNodes.LOG,
        parent_node=action2_node.path,
    )
    stage.push_command(flow_node2_create_command)
    stage.push_command(child_node2_create_command)

    action2_flow_start = action2_node.find_flow_start_node()
    action2_child = child_node2_create_command.result_node

    # Setup flow connections
    root_flow_start_node["flow"] >> action1_node["flow"]
    action1_node["flow"] >> action2_node["flow"]

    action1_flow_start["flow"] >> action1_child["flow"]
    action2_flow_start["flow"] >> action2_child["flow"]

    # Setup messages
    action1_node["message"].push_value("ACTION1")
    action2_node["message"].push_value("ACTION2")
    action1_child["message"].push_value("ACTION1_CHILD")
    action2_child["message"].push_value("ACTION2_CHILD")

    # Perform stage crawl
    stage.crawler.start()
    stage.export_json(export_path)
    assert stage.crawler.visited_node_paths == [
        stage.root_node.path.as_posix(),
        root_flow_start_node.path.as_posix(),
        action1_node.path.as_posix(),
        action1_flow_start.path.as_posix(),
        action1_child.path.as_posix(),
        action2_node.path.as_posix(),
        action2_flow_start.path.as_posix(),
        action2_child.path.as_posix(),
    ]
    assert stage.crawler._execution_paths_stack == stage.crawler.visited_node_paths


# ======== Traversal ========= #


def make_node(stage, type_id=CoreNodes.ACTION, parent=None, name=None):
    command = commands.CreateNodeCommand(
        stage=stage, type_id=type_id, parent_node=parent, name=name
    )
    stage.push_command(command)
    return command.result_node


def executed_names(stage):
    return [
        pathlib.PurePosixPath(path).name for path in stage.crawler.execution_paths_stack
    ]


def test_long_flow_chain_is_not_limited_by_the_recursion_limit():
    stage = Stage()
    previous = make_node(stage, CoreNodes.FLOW_START, name="start")
    length = 1500  # more than the recursion limit
    for index in range(length):
        node = make_node(stage, name=f"n{index}")
        previous["flow"] >> node["flow"]
        previous = node

    stage.crawler.start()

    assert len(stage.crawler.visited_node_paths) == length + 2  # root and start too
    assert executed_names(stage)[-1] == f"n{length - 1}"


def test_sequence_outputs_are_followed_depth_first_in_order():
    stage = Stage()
    start = make_node(stage, CoreNodes.FLOW_START, name="start")
    sequence = make_node(stage, CoreNodes.SEQUENCE, name="seq")
    first = make_node(stage, name="a1")
    second = make_node(stage, name="a2")
    other = make_node(stage, name="b1")
    start["flow"] >> sequence["flow_0"]
    sequence["flow_1"] >> first["flow"]
    first["flow"] >> second["flow"]
    sequence["flow_2"] >> other["flow"]

    stage.crawler.start()

    assert executed_names(stage) == ["stage", "start", "seq", "a1", "a2", "b1"]


def test_inactive_flow_output_is_not_followed():
    stage = Stage()
    start = make_node(stage, CoreNodes.FLOW_START, name="start")
    sequence = make_node(stage, CoreNodes.SEQUENCE, name="seq")
    followed = make_node(stage, name="followed")
    skipped = make_node(stage, name="skipped")
    start["flow"] >> sequence["flow_0"]
    sequence["flow_1"] >> followed["flow"]
    sequence["flow_2"] >> skipped["flow"]
    sequence["flow_2"].is_active = False

    stage.crawler.start()

    assert "followed" in executed_names(stage)
    assert "skipped" not in executed_names(stage)


def test_converging_flows_run_the_shared_node_once():
    stage = Stage()
    start = make_node(stage, CoreNodes.FLOW_START, name="start")
    sequence = make_node(stage, CoreNodes.SEQUENCE, name="seq")
    left = make_node(stage, name="left")
    right = make_node(stage, name="right")
    shared = make_node(stage, name="shared")
    tail = make_node(stage, name="tail")
    start["flow"] >> sequence["flow_0"]
    sequence["flow_1"] >> left["flow"]
    sequence["flow_2"] >> right["flow"]
    left["flow"] >> shared["flow"]
    right["flow"] >> shared["flow"]
    shared["flow"] >> tail["flow"]

    stage.crawler.start()

    assert executed_names(stage).count("shared") == 1
    assert executed_names(stage).count("tail") == 1


def test_cycle_ends_instead_of_running_forever():
    stage = Stage()
    start = make_node(stage, CoreNodes.FLOW_START, name="start")
    first = make_node(stage, name="first")
    second = make_node(stage, name="second")
    start["flow"] >> first["flow"]
    first["flow"] >> second["flow"]
    second["flow"] >> first["flow"]

    stage.crawler.start()

    assert executed_names(stage).count("first") == 1
    assert executed_names(stage).count("second") == 1


def test_flow_pointing_at_a_node_that_is_not_a_sibling_raises():
    stage = Stage()
    start = make_node(stage, CoreNodes.FLOW_START, name="start")
    first = make_node(stage, name="first")
    holder = make_node(stage, name="holder")
    inner = make_node(stage, parent=holder, name="inner")
    start["flow"] >> first["flow"]
    first["flow"] >> inner["flow"]

    with pytest.raises(RuntimeError, match="not a sibling"):
        stage.crawler.start()


def test_visiting_a_node_directly_runs_it():
    stage = Stage()
    node = make_node(stage, name="direct")

    node.accept_visitor(stage.crawler)

    assert executed_names(stage) == ["direct"]


def test_crawler_can_run_again_after_an_error():
    stage = Stage()
    start = make_node(stage, CoreNodes.FLOW_START, name="start")
    first = make_node(stage, name="first")
    holder = make_node(stage, name="holder")
    inner = make_node(stage, parent=holder, name="inner")
    start["flow"] >> first["flow"]
    first["flow"] >> inner["flow"]
    with pytest.raises(RuntimeError):
        stage.crawler.start()

    first["flow"].is_active = False
    stage.crawler.start()

    assert executed_names(stage) == ["stage", "start", "first"]


def make_loop(stage, first, last):
    loop = make_node(stage, CoreNodes.FOR_LOOP, name="loop")
    loop["first_index"].push_value(first)
    loop["last_index"].push_value(last)
    return loop


def test_for_loop_runs_body_for_every_index_then_completed():
    stage = Stage()
    start = make_node(stage, CoreNodes.FLOW_START, name="start")
    loop = make_loop(stage, 0, 3)
    body1 = make_node(stage, name="body1")
    body2 = make_node(stage, name="body2")
    done = make_node(stage, name="done")
    start["flow"] >> loop["flow"]
    loop["loop_body"] >> body1["flow"]
    body1["flow"] >> body2["flow"]
    loop["completed"] >> done["flow"]

    stage.crawler.start()

    assert executed_names(stage) == (
        ["stage", "start"] + ["body1", "body2"] * 4 + ["loop", "done"]
    )
    assert loop["index"].pull_value() == 3


@pytest.mark.parametrize(("first", "last", "runs"), [(2, 2, 1), (3, 1, 0)])
def test_for_loop_edge_ranges(first, last, runs):
    stage = Stage()
    start = make_node(stage, CoreNodes.FLOW_START, name="start")
    loop = make_loop(stage, first, last)
    body = make_node(stage, name="body")
    done = make_node(stage, name="done")
    start["flow"] >> loop["flow"]
    loop["loop_body"] >> body["flow"]
    loop["completed"] >> done["flow"]

    stage.crawler.start()

    assert executed_names(stage).count("body") == runs
    assert executed_names(stage)[-1] == "done"
