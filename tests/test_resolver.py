import pathlib
from nyx import get_main_logger, get_logger
from nyx.core import Stage
from nyx.core import Node

LOGGER = get_main_logger()
TEST_LOGGER = get_logger(__name__)


def test_compute_relative_path():
    stage = Stage()

    # Case1 different parents
    path1 = pathlib.PurePosixPath("/node1/child1")
    path2 = pathlib.PurePosixPath("/node2/child2")

    rel_path = stage.resolver.compute_relative_path(path1, path2)
    assert rel_path.as_posix() == "../../node2/child2"


def test_compute_absolute_path():
    stage = Stage()
    node1 = Node(name="node1")

    stage.add_node(node1)
