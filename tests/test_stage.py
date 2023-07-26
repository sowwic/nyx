import pathlib
from collections import OrderedDict

from nyx import get_main_logger, get_logger
from nyx.core import Stage
from nyx.core import Node
from nyx.utils import file_fn

LOGGER = get_main_logger()
TEST_LOGGER = get_logger(__name__)


def test_stage_create_empty():
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
    assert stage.serialize() == file_fn.load_json(
        export_path, object_pairs_hook=OrderedDict)


def test_stage_deserialize(output_dir: pathlib.Path):
    stage = Stage()
    export_path = output_dir / \
        f"test_stage_deserialize_export{stage.FILE_EXTENSION}"
    export_path2 = output_dir / \
        f"test_stage_deserialize_check{stage.FILE_EXTENSION}"
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


def test_stage_get_node_from_path_root():
    stage = Stage()
    node = Node()

    added_nodes = []
    for i in range(5):
        node = Node()
        stage.add_node(node)
        added_nodes.append(node)

    assert stage.get_node_children_from_path("/") == added_nodes
    assert stage.get_node_children_from_path("/") == stage.list_top_nodes()


def test_stage_get_node_from_path():
    stage = Stage()
    node = Node()
    stage.add_node(node)

    for i in range(5):
        Node(parent=node)

    assert stage.get_node_children_from_path("/node") == node.list_children()


def test_stage_export_import_with_connections(output_dir: pathlib.Path):
    export_path = output_dir / \
        f"test_stage_export_import_with_connections{Stage.FILE_EXTENSION}"

    stage1 = Stage()
    node1 = Node()
    node2 = Node()
    stage1.add_node(node1)
    stage1.add_node(node2)

    # Add attributes
    node1.add_attr("count", 5)
    node2.add_attr("test")

    # Connetions
    node2.set_input_exec_path(node1)
    node1.attr("count").connect(node2.attr("test"))

    stage1.export_json(export_path)

    stage2 = Stage()
    stage2.import_json(export_path)

    assert stage1.serialize() == stage2.serialize()


def test_stage_set_stage_execution_start():
    stage = Stage()
    node1 = Node()
    node2 = Node()
    node3 = Node()

    stage.add_node(node1)
    stage.add_node(node2)
    stage.add_node(node3)

    stage.set_execution_start_path(None, node1)
    TEST_LOGGER.debug(stage.describe())

    assert stage.get_execution_start_path(
        None, serializable=False) == node1.path


def test_stage_set_execution_start_set_export_import(output_dir: pathlib.Path):
    export_path = output_dir / \
        f"test_stage_set_execution_start_set_export_import{Stage.FILE_EXTENSION}"

    stage = Stage()
    node1 = Node()
    node2 = Node()
    node3 = Node()

    stage.add_node(node1)
    stage.add_node(node2, parent=node1)
    stage.add_node(node3, parent=node1)

    stage.set_execution_start_path(None, node1)
    stage.set_execution_start_path(node1, node2)

    stage.export_json(export_path)

    stage2 = Stage()
    stage2.import_json(export_path)

    assert stage2.node(
        "/node").get_execution_start_path(serializable=True) == "/node/node"
    assert stage.serialize() == stage2.serialize()


def test_stage_convert_to_node():
    # Original stage
    stage = Stage()
    node1 = Node()
    node2 = Node()

    stage.add_node(node1)
    stage.add_node(node2)

    # Final stage
    main_stage = Stage()
    stage_node = Node()

    node_name = "new_stage_node"
    serialized_stage_node = Stage.convert_stage_to_node(stage, name=node_name)

    main_stage.add_node(stage_node)
    stage_node.deserialize(serialized_stage_node, restore_id=True)
    TEST_LOGGER.debug(main_stage.describe())

    new_child_paths = [stage_node.path /
                       node1.path.name, stage_node.path / node2.path.name]
    assert stage_node.name == node_name
    assert stage_node.list_children_paths() == new_child_paths
