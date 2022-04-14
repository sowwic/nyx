from nyx.core import Stage
from nyx.core import Node


def test_create_node_at_root():
    node_name = "node"

    stage = Stage()
    node = Node(stage, name=node_name, parent_path="/")

    assert node.model.path.as_posix() == f"/{node_name}"


def test_create_node_as_child():
    node1_name = "node1"
    node2_name = "node2"
    node3_name = "node3"
    node4_name = "node4"
    node5_name = "node5"

    stage = Stage()
    node1 = Node(stage, name=node1_name, parent_path="/")
    node2 = Node(stage, name=node2_name, parent_path=node1.model.path)
    node3 = Node(stage, name=node3_name, parent_path=node2.model.path)

    node4 = Node(stage, name=node4_name, parent_path=stage.ROOT_PATH)
    node5 = Node(stage, name=node5_name, parent_path=node4.model.path)

    stage.add_node(node1)
    stage.add_node(node2)
    stage.add_node(node3)

    stage.add_node(node4)
    stage.add_node(node5)

    assert stage.data == {"node1": {"node2": {"node3": {}}}, "node4": {"node5": {}}}
