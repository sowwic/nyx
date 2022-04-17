import pathlib
from nyx.core import Stage
from nyx.core import Node


def test_create_empty_stage():
    Stage()


def test_stage_export_import_json(output_dir: pathlib.Path):
    stage = Stage()
    export_path = output_dir / f"test_stage_export{stage.FILE_EXTENSION}"
    # Add nodes
    for index in range(1, 5):
        base_node = Node("node")
        base_node["count"] = 5
        stage.add_node(base_node)
        for child_index in range(1, 6):
            child_node = Node("child_node")
            stage.add_node(child_node, base_node)
            for deep_index in range(1, 4):
                leaf_node = Node("leaf_node")
                stage.add_node(leaf_node, child_node)

    stage.export_json(export_path)
    assert export_path.is_file()

    # Import data and compare with stage serialized
    json_data = stage.import_json(export_path)
    assert stage.serialize() == json_data
