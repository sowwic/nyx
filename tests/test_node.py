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
    child_node1 = Node("node")
    child_node2 = Node("node")

    stage.add_node(parent_node)
    stage.add_node(child_node1, parent=parent_node)
    stage.add_node(child_node2, parent=parent_node)

    assert [child_node1, child_node2] == parent_node.list_children()
    assert [parent_node] == list(child_node1.list_parents())
    assert [parent_node] == list(child_node2.list_parents())
    assert [parent_node, child_node1] == list(child_node1.path())
    assert [parent_node, child_node2] == list(child_node2.path())
