import pathlib
from nyx import get_main_logger, get_logger
from nyx.core.resolver import Resolver

LOGGER = get_main_logger()
TEST_LOGGER = get_logger(__name__)


def test_compute_relative_path():
    resolver = Resolver()

    # Case1 different parents
    path1 = pathlib.PurePosixPath("/node1/child1")
    path2 = pathlib.PurePosixPath("/node2/child2")
    rel_path = resolver.compute_relative_path(path1, path2)
    assert rel_path.as_posix() == "../../node2/child2"

    # Case2 rel path to child
    path1 = pathlib.PurePosixPath("/node1/child1")
    path2 = pathlib.PurePosixPath("/node1/child1/child2")
    rel_path = resolver.compute_relative_path(path1, path2)
    assert rel_path.as_posix() == "child2"

    # Case3 rel path to 2nd child
    path1 = pathlib.PurePosixPath("/node1/child1")
    path2 = pathlib.PurePosixPath("/node1/child1/child2/child3")
    rel_path = resolver.compute_relative_path(path1, path2)
    assert rel_path.as_posix() == "child2/child3"


def test_compute_absolute_child_path():
    resolver = Resolver()
    node1_path = pathlib.PurePosixPath("/node1")
    assert resolver.computer_absolute_path(
        node1_path, "child1").as_posix() == "/node1/child1"
    assert resolver.computer_absolute_path(
        node1_path, "child1/child2").as_posix() == "/node1/child1/child2"


def test_compute_absolute_path_other_node_child():
    resolver = Resolver()
    child1_path = pathlib.PurePosixPath("/node1/child1")
    child2_path = pathlib.PurePosixPath("/node2/child2")
    path_to_child2 = "../../node2/child2"
    assert resolver.computer_absolute_path(
        child1_path, path_to_child2) == child2_path


def test_compute_absolute_path_same_node_child():
    resolver = Resolver()
    child1_path = pathlib.PurePosixPath("/node1/child1")
    child2_path = pathlib.PurePosixPath("/node1/child2")
    path_to_child2 = "../child2"
    assert resolver.computer_absolute_path(
        child1_path, path_to_child2) == child2_path
