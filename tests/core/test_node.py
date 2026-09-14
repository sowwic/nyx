import logging

from nyx.core import Node, Stage

LOGGER = logging.getLogger(__name__)


def test_add_node_to_root():
    stage = Stage()
    node = Node("node")

    stage.add_node(node)

    assert stage.root_node.hasChildren()
    assert stage.root_node.child(0) is node


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


def test_node_execute_while_active():
    stage = Stage()
    node = Node("node")
    stage.add_node(node)

    node.execute()

    assert node.is_active()


def test_node_execute_while_not_active():
    stage = Stage()
    node = Node("node")
    stage.add_node(node)

    node.set_active(False)

    node.execute()

    assert not node.is_active()
    # TODO add asserts for component values


def test_node_list_children_tree():
    stage = Stage()
    node = Node()
    stage.add_node(node)

    par = node

    added_nodes = []
    for _ in range(5):
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
        # ["/", "stage", "cool_name"]
        assert child.path.parts[2] == new_name
        assert child.path in stage.path_map


def test_node_delete_first_paths_map_valid():
    stage = Stage()
    node = Node()
    stage.add_node(node)

    par = node

    for _ in range(5):
        par = Node(parent=par)
    LOGGER.debug(f"Path map: {stage.path_map}")

    node.delete()
    LOGGER.debug(f"Path map after deletion: {stage.path_map}")

    assert len(stage.path_map) == 1
    assert stage.path_map.get(stage.ROOT_NODE_PATH) is not None


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
