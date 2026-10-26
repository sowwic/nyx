import pathlib
import pytest

from nyx.api.v1 import Stage, commands, CoreNodes, CoreNodeComponents


def test_node_deserialization_restores_uuids_for_all_components(
    output_dir: pathlib.Path, request: pytest.FixtureRequest
):
    stage = Stage()
    export_path = output_dir / f"{request.node.name}_export{stage.FILE_EXTENSION}"

    node_command = commands.CreateNodeCommand(
        stage=stage, name="test", type_id=CoreNodes.ACTION
    )
    stage.push_command(node_command)
    node = node_command.result_node

    bool_value_command = commands.AddNodeComponentCommand(
        node=node, type_id=CoreNodeComponents.VALUE, name="test_bool"
    )
    comment_command = commands.AddNodeComponentCommand(
        node=node, type_id=CoreNodeComponents.COMMENT, name="note"
    )
    script_command = commands.AddNodeComponentCommand(
        node=node, type_id=CoreNodeComponents.SCRIPT, name="cool_script"
    )

    stage.push_command(bool_value_command, comment_command, script_command)
    stage.export_json(file_path=export_path)

    other_stage = Stage()
    other_stage.import_json(export_path)

    assert stage.root_node.serialize() == other_stage.root_node.serialize()
    assert len(stage.uuid_map) == len(other_stage.uuid_map)
    for uuid, stage_object in stage.uuid_map.items():
        assert uuid in other_stage.uuid_map.keys()
        assert stage_object.path == other_stage.uuid_map[uuid].path
