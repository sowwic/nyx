import logging
from collections import deque

from nyx.core import Node, Stage

LOGGER = logging.getLogger(__name__)


def test_handler_build_queue_from_stage():
    stage = Stage()

    root_node1 = Node("root_node1")
    root_node2 = Node("root_node2")
    root_node3 = Node("root_node3")
    stage.add_node([root_node1, root_node2, root_node3])
    stage.set_execution_start_path(None, root_node1)

    root_node1.set_output_exec_path(root_node2)
    root_node2.set_output_exec_path(root_node3)

    queue = stage.handler.build_execution_queue()
    # LOGGER.debug(stage.describe())
    LOGGER.debug(f"Exec queue: {queue}")

    expected_queue = deque(
        [root_node1.cached_path, root_node2.cached_path, root_node3.cached_path]
    )
    assert expected_queue == queue


def test_handler_build_queue_with_children():
    stage = Stage()

    # Root nodes
    root_node1 = Node("root_node1")
    root_node2 = Node("root_node2")
    root_node3 = Node("root_node3")
    stage.add_node([root_node1, root_node2, root_node3])
    stage.set_execution_start_path(None, root_node1)

    root_node1.set_output_exec_path(root_node2)
    root_node2.set_output_exec_path(root_node3)

    # Root node1 children
    child1_1 = Node("child1_1", parent=root_node1)
    child1_2 = Node("child1_2", parent=root_node1)
    child1_3 = Node("child1_3", parent=root_node1)
    child1_1.set_output_exec_path(child1_2)
    child1_2.set_output_exec_path(child1_3)

    root_node1.set_execution_start_path(child1_1)

    queue = stage.handler.build_execution_queue()
    LOGGER.debug(queue)
    expected_queue = deque(
        [
            root_node1.cached_path,
            child1_1.cached_path,
            child1_2.cached_path,
            child1_3.cached_path,
            root_node2.cached_path,
            root_node3.cached_path,
        ]
    )

    assert expected_queue == queue


def test_handler_run():
    stage = Stage()

    root_node1 = Node("root_node1")
    root_node2 = Node("root_node2")
    root_node3 = Node("root_node3")
    stage.add_node([root_node1, root_node2, root_node3])
    stage.set_execution_start_path(None, root_node1)

    root_node1.set_output_exec_path(root_node2)
    root_node2.set_output_exec_path(root_node3)

    # Root node1 children
    child1_1 = Node("child1_1", parent=root_node1)
    child1_2 = Node("child1_2", parent=root_node1)
    child1_3 = Node("child1_3", parent=root_node1)
    child1_1.set_output_exec_path(child1_2)
    child1_2.set_output_exec_path(child1_3)
    root_node1.set_execution_start_path(child1_1)

    queue = stage.handler.build_execution_queue()
    LOGGER.debug(f"Exec queue: {queue}")

    # LOGGER.debug(stage.describe())
    stage.handler.run()

    # TODO: add asserts for components values
