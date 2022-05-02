from nyx import get_main_logger, get_logger
from nyx.core import Stage
from nyx.core import Node

LOGGER = get_main_logger()
TEST_LOGGER = get_logger(__name__)


def test_add_node_to_root():
    stage = Stage()
    node = Node("node")

    stage.add_node(node)

    root = stage.invisibleRootItem()
    assert root.hasChildren()
    assert root.child(0) is node


def test_add_node_with_parent():
    stage = Stage()
    parent_node = Node("node")
    stage.add_node(parent_node)

    child_node1 = Node("node", parent=parent_node)
    child_node2 = Node("node", parent=parent_node)

    assert [child_node1, child_node2] == parent_node.list_children()
    assert [parent_node] == child_node1.list_parents()
    assert [parent_node] == child_node2.list_parents()


def test_add_node_with_parent_via_stage():
    stage = Stage()
    parent_node = Node("node")
    stage.add_node(parent_node)

    child_node1 = Node("node")
    child_node2 = Node("node")

    stage.add_node([child_node1, child_node2], parent=parent_node)

    assert [child_node1, child_node2] == parent_node.list_children()
    assert [parent_node] == child_node1.list_parents()
    assert [parent_node] == child_node2.list_parents()


def test_node_delete_mid_children():
    stage = Stage()
    parent_node = Node("node")
    stage.add_node(parent_node)

    for index in range(1, 5):
        Node(parent=parent_node)

    assert len(parent_node.list_children()) == 4
    first, second, third, fourth = parent_node.list_children()
    second.delete()
    third.delete()
    assert parent_node.list_children() == [first, fourth]


def test_node_execute_code_while_active():
    stage = Stage()
    node = Node("node")
    stage.add_node(node)

    node.add_attr("test")

    code = 'self["test"].push(5)'
    node.set_python_code(code)
    node.execute_code()

    assert node.is_active()
    assert node["test"].value is None
    assert node["test"].resolved_value is None
    assert node["test"].cached_value == 5


def test_node_execute_code_while_not_active():
    stage = Stage()
    node = Node("node")
    stage.add_node(node)

    node.add_attr("test")
    node.set_active(False)

    code = 'self["test"].push(5)'
    node.set_python_code(code)
    node.execute_code()

    assert not node.is_active()
    assert node["test"].value is None
    assert node["test"].resolved_value is None
    assert node["test"].cached_value is None


def test_node_list_children_tree():
    stage = Stage()
    node = Node()
    stage.add_node(node)

    par = node

    added_nodes = []
    for i in range(5):
        par = Node(parent=par)
        added_nodes.append(par)

    assert node.list_children_tree() == added_nodes


def test_node_rename():
    stage = Stage()
    node = Node()
    stage.add_node(node)

    # Create nested child nodes
    par = node
    for i in range(5):
        par = Node(parent=par)

    # Store old data
    children = node.list_children_tree()
    old_path = node.path
    old_child_paths = [child.path for child in children]

    # Do rename of first node
    new_name = "cool_name"
    node.rename(new_name)

    # Assertions
    assert node._cached_path == node.path
    assert old_path not in stage.path_map
    for old_child_path in old_child_paths:
        assert old_child_path not in stage.path_map

    for child in children:
        assert child.path.parts[1] == new_name
        assert child.path in stage.path_map


def test_node_delete_first_paths_map_valid():
    stage = Stage()
    node = Node()
    stage.add_node(node)

    par = node

    for i in range(5):
        par = Node(parent=par)
    TEST_LOGGER.debug(f"Path map: {stage.path_map}")

    node.delete()
    TEST_LOGGER.debug(f"Path map after deletion: {stage.path_map}")

    assert stage.path_map == {}


def test_node_delete_mid_paths_map_valid():
    stage = Stage()
    node = Node()
    stage.add_node(node)

    par = node

    added_nodes = []
    for i in range(5):
        par = Node(parent=par)
        added_nodes.append(par)

    TEST_LOGGER.debug(f"Path map: {stage.path_map}")
    added_nodes[1].delete()

    TEST_LOGGER.debug(f"Path map after deletion: {stage.path_map}")

    assert stage.path_map != {}
    assert node.path in stage.path_map
    for child in node.list_children_tree():
        assert child.path in stage.path_map


def test_node_cache_attributes():
    stage = Stage()
    node = Node()
    stage.add_node(node)

    node.add_attr("test1", value=5, resolve=True)
    node.add_attr("test2", value=10, resolve=True)
    node.add_attr("test3", value=15, resolve=True)

    for attr in node.attribs.values():
        assert not attr.is_cached()

    node.cache_attributes_values()
    for attr in node.attribs.values():
        assert attr.is_cached()

    node.clear_attributes_caches()
    for attr in node.attribs.values():
        assert not attr.is_cached()

    node.cache_attributes_values()
    for attr in node.attribs.values():
        assert attr.is_cached()


def test_node_set_exec_input():
    stage = Stage()
    node1 = Node()
    node2 = Node()
    stage.add_node(node1)
    stage.add_node(node2)

    node2.set_input_exec_path(node1)
    assert node2.get_input_exec_path() == node1.path.as_posix()
    assert node1.get_output_exec_path() == node2.path.as_posix()


def test_node_set_exec_input_deep_hierarchy():
    stage = Stage()
    node = Node()
    stage.add_node(node)
    child1 = Node(parent=node)
    child2 = Node(parent=child1)

    node1 = Node(parent=child2)
    node2 = Node(parent=child2)

    node2.set_input_exec_path(node1)
    assert node2.get_input_exec_path() == node1.path.as_posix()
    assert node1.get_output_exec_path() == node2.path.as_posix()


def test_node_set_exec_output():
    stage = Stage()
    node1 = Node()
    node2 = Node()
    stage.add_node(node1)
    stage.add_node(node2)

    node1.set_output_exec_path(node2)
    assert node2.get_input_exec_path() == node1.path.as_posix()
    assert node1.get_output_exec_path() == node2.path.as_posix()


def test_node_set_input_exec_reconnect():
    stage = Stage()
    node1 = Node()
    node2 = Node()
    node3 = Node()
    stage.add_node(node1)
    stage.add_node(node2)
    stage.add_node(node3)

    node2.set_input_exec_path(node1)
    node2.set_input_exec_path(node3)
    assert node2.get_input_exec_path() == node3.path.as_posix()
    assert node3.get_output_exec_path() == node2.path.as_posix()
    assert node1.get_output_exec_path() == ""


def test_node_set_exec_input_out_of_scope():
    stage = Stage()
    node = Node()
    stage.add_node(node)
    child1 = Node(parent=node)
    child2 = Node(parent=child1)

    node1 = Node(parent=child2)
    node2 = Node(parent=child2)

    leaf1 = Node(name="leaf1", parent=node1)
    leaf2 = Node(name="leaf2", parent=node2)

    leaf1.set_input_exec_path(leaf2)
    assert leaf1.get_input_exec_path() == ""
    assert leaf2.get_output_exec_path() == ""


def test_node_set_execution_start():
    stage = Stage()
    node1 = Node()
    node2 = Node()
    node3 = Node()

    stage.add_node(node1)
    stage.add_node(node2, parent=node1)
    stage.add_node(node3, parent=node1)

    stage.set_execution_start_path(None, node1)
    stage.set_execution_start_path(node1, node2)
    TEST_LOGGER.debug(stage.describe())

    assert stage.get_execution_start_path(node1) == node2.path
    assert stage.get_execution_start_path(None, serializable=False) == node1.path
