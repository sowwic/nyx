from collections import deque

from nyx import get_main_logger, get_logger
from nyx.core import Stage
from nyx.core import Node

LOGGER = get_main_logger()
TEST_LOGGER = get_logger(__name__)


def test_executor_build_queue_from_stage():
    stage = Stage()

    root_node1 = Node("root_node1")
    root_node2 = Node("root_node2")
    root_node3 = Node("root_node3")
    stage.add_node([root_node1, root_node2, root_node3])
    stage.set_execution_start_path(None, root_node1)

    root_node1.set_output_exec_path(root_node2)
    root_node2.set_output_exec_path(root_node3)

    executor_queue = stage.executor.build_execution_queue()
    # TEST_LOGGER.debug(stage.describe())
    TEST_LOGGER.debug(f"Exec queue: {executor_queue}")

    expected_queue = deque([root_node1.cached_path, root_node2.cached_path, root_node3.cached_path])
    assert expected_queue == executor_queue


def test_executor_build_queue_with_children():
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

    executor_queue = stage.executor.build_execution_queue()
    TEST_LOGGER.debug(executor_queue)
    expected_queue = deque([root_node1.cached_path,
                           child1_1.cached_path,
                           child1_2.cached_path,
                           child1_3.cached_path,
                           root_node2.cached_path,
                           root_node3.cached_path])

    assert expected_queue == executor_queue


def test_executor_run():
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

    executor_queue = stage.executor.build_execution_queue()
    TEST_LOGGER.debug(f"Exec queue: {executor_queue}")

    # Root Attributes
    root_node1.add_attr("test1")
    root_node2.add_attr("test2")
    root_node3.add_attr("test3")

    root_node1.set_python_code("self.attr('test1').push(5)")
    root_node2.set_python_code("self.attr('test2').push(10)")
    root_node3.set_python_code("self.attr('test3').push(15)")

    # Child attributes
    # Root Attributes
    child1_1.add_attr("child_test1")
    child1_2.add_attr("child_test2")
    child1_3.add_attr("child_test3", value="/root_node1/child1_2.child_test2")

    child1_1.set_python_code("self.attr('child_test1').push(5)")
    child1_2.set_python_code("self.attr('child_test2').push(10)")

    # TEST_LOGGER.debug(stage.describe())
    stage.executor.run()

    TEST_LOGGER.debug(f"ATTR: {child1_3['child_test3']}")

    assert root_node1.attr("test1").cached_value == 5
    assert root_node2.attr("test2").cached_value == 10
    assert root_node3.attr("test3").cached_value == 15

    assert child1_1.attr("child_test1").cached_value == 5
    assert child1_2.attr("child_test2").cached_value == 10
    assert child1_3.attr("child_test3").cached_value == 10
