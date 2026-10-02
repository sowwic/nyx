import pathlib
import pytest

from nyx.api.v1 import Stage, commands, CoreNodes, CoreNodeComponents


def test_adding_combination_of_components(
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
