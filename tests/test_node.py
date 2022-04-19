from nyx import get_main_logger
from nyx.core import Stage
from nyx.core import Node

LOGGER = get_main_logger()


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


def test_node_code_exec():
    stage = Stage()
    node = Node("node")
    stage.add_node(node)

    code = 'self["test"] = 5'
    node.set_python_code(code)
    node.execute_code()

    assert node["test"].value == 5


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
        assert child.path.parts[0] == new_name
        assert child.path in stage.path_map


def test_node_delete_first_paths_map_valid():
    stage = Stage()
    node = Node()
    stage.add_node(node)

    par = node

    for i in range(5):
        par = Node(parent=par)
    LOGGER.debug(f"Path map: {stage.path_map}")

    node.delete()
    LOGGER.debug(f"Path map after deletion: {stage.path_map}")

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

    LOGGER.debug(f"Path map: {stage.path_map}")
    added_nodes[1].delete()

    LOGGER.debug(f"Path map after deletion: {stage.path_map}")

    assert stage.path_map != {}
    assert node.path in stage.path_map
    for child in node.list_children_tree():
        assert child.path in stage.path_map
