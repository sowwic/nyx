import pathlib
from collections import OrderedDict

from nyx import get_main_logger
from nyx.core import Stage
from nyx.core import Node
from nyx.utils import file_fn

LOGGER = get_main_logger()


def test_create_empty_stage():
    stage = Stage()
    assert stage.path_map == {}
    assert stage.undo_stack.isClean()
    assert stage.list_top_nodes() == []


def test_stage_export_import_json(output_dir: pathlib.Path):
    stage = Stage()
    export_path = output_dir / f"test_stage_export{stage.FILE_EXTENSION}"
    # Add nodes
    for index in range(3):
        base_node = Node("node")
        base_node["count"] = 5
        stage.add_node(base_node)
        for child_index in range(3):
            child_node = Node("child_node", base_node)
            for deep_index in range(2):
                leaf_node = Node("leaf_node", child_node)
                leaf_node["count"] = 10
                leaf_node["test"] = True

    stage.export_json(export_path)
    assert export_path.is_file()

    # Import data and compare with stage serialized
    assert stage.serialize() == file_fn.load_json(export_path, object_pairs_hook=OrderedDict)


def test_stage_deserialize(output_dir: pathlib.Path):
    stage = Stage()
    export_path = output_dir / f"test_stage_deserialize_export{stage.FILE_EXTENSION}"
    export_path2 = output_dir / f"test_stage_deserialize_check{stage.FILE_EXTENSION}"
    for index in range(3):
        base_node = Node("node")
        base_node["count"] = 5
        stage.add_node(base_node)
        for child_index in range(3):
            child_node = Node("child_node", base_node)
            for deep_index in range(2):
                leaf_node = Node("leaf_node", child_node)
                leaf_node["count"] = 10
                leaf_node["test"] = True

    stage.export_json(export_path)

    stage2 = Stage()
    stage2.import_json(export_path)
    stage2.export_json(export_path2)

    assert stage2.serialize() == stage.serialize()


def test_stage_get_parent_node_from_relative_path():
    stage = Stage()
    node = Node()
    stage.add_node(node)

    child1 = Node("child1", parent=node)
    child2 = Node("child2", parent=node)

    leaf1 = Node("leaf1", parent=child1)
    leaf2 = Node("leaf2", parent=child2)

    # Backward
    assert stage.get_node_from_relative_path(leaf1, ".") is leaf1
    assert stage.get_node_from_relative_path(leaf1, "..") is child1
    assert stage.get_node_from_relative_path(leaf1, "../..") is node
    assert stage.get_node_from_relative_path(leaf1, "../../child2") is child2
    assert stage.get_node_from_relative_path(leaf1, "../../child2/leaf2") is leaf2


def test_stage_get_child_node_from_relative_path():
    stage = Stage()
    node = Node()
    stage.add_node(node)

    child1 = Node("child1", parent=node)
    child2 = Node("child2", parent=node)

    leaf1 = Node("leaf1", parent=child1)
    leaf2 = Node("leaf2", parent=child2)

    # Forward path
    assert stage.get_node_from_relative_path(child1, "./leaf1") is leaf1
    assert stage.get_node_from_relative_path(node, "./child1/leaf1") is leaf1
    assert stage.get_node_from_relative_path(child2, "./leaf2") is leaf2
    assert stage.get_node_from_relative_path(node, "./child2/leaf2") is leaf2


def test_stage_invalid_relative_path_returns_none():
    stage = Stage()
    node = Node()
    stage.add_node(node)

    # Invalid path
    assert stage.get_node_from_relative_path(node, "../..") is None
    assert stage.get_node_from_relative_path(node, "./child1/leaf") is None
    assert stage.get_node_from_relative_path(node, "./child1/../leaf") is None


def test_get_relative_path_to():
    stage = Stage()
    node = Node()
    stage.add_node(node)

    child1 = Node("child1", parent=node)
    child2 = Node("child2", parent=node)

    leaf1 = Node("leaf1", parent=child1)
    leaf2 = Node("leaf2", parent=child2)

    rel_leaf1_to_leaf2 = stage.get_relative_path_to(leaf1, leaf2)
    LOGGER.debug(f"leaf_1 -> leaf_2: {rel_leaf1_to_leaf2}")
    assert stage.get_node_from_relative_path(leaf1, rel_leaf1_to_leaf2) is leaf2
