from nyx.core import Stage
from nyx.core import Node


def test_create_node_at_root():
    node_name = "node"

    stage = Stage()
    node = Node(stage, name=node_name, parent_path="/")

    assert node.model.path.as_posix() == f"/{node_name}"


if __name__ == "__main__":
    test_create_node_at_root()
