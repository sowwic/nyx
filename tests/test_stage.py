import pathlib
from nyx.core import Stage
from nyx.core import Node


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
    json_data = stage.import_json(export_path)
    assert stage.serialize() == json_data
