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
    child_node1 = Node("node", parent=parent_node)
    child_node2 = Node("node", parent=parent_node)

    stage.add_node(parent_node)

    assert [child_node1, child_node2] == parent_node.list_children()
    assert [parent_node] == child_node1.list_parents()
    assert [parent_node] == child_node2.list_parents()
    assert [parent_node, child_node1] == child_node1.path()
    assert [parent_node, child_node2] == child_node2.path()


def test_node_delete_mid_children():
    stage = Stage()
    parent_node = Node("node")
    stage.add_node(parent_node)

    for index in range(1, 5):
        node = Node(f"node{index}", parent=parent_node)
        stage.add_node(node)

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
