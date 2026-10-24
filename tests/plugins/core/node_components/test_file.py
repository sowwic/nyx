import pathlib

from nyx.api.v1 import (
    CoreDatatypes,
    CoreNodeComponents,
    CoreNodes,
    NodeComponentFlag,
    Stage,
    commands,
)


def add_file_component(stage: Stage, name: str = "file"):
    node_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.ACTION)
    stage.push_command(node_command)
    component_command = commands.AddNodeComponentCommand(
        node=node_command.result_node, type_id=CoreNodeComponents.FILE, name=name
    )
    stage.push_command(component_command)
    return component_command.result_component


def test_file_component_is_a_string_with_a_file_editor():
    component = add_file_component(Stage())

    assert component.get_type_id() == CoreNodeComponents.FILE
    assert component.datatype_id == CoreDatatypes.STRING
    assert component.raw_value == ""
    assert component.is_editable
    assert component.is_static
    assert component.EDITOR_QML == "FileComponentItem"
    assert NodeComponentFlag.EDITABLE in component.component_flags


def test_file_component_keeps_the_path_over_save_and_load(tmp_path: pathlib.Path):
    stage = Stage()
    component = add_file_component(stage)
    path = tmp_path / "data.txt"
    component.push_value(str(path))
    stage_file = tmp_path / f"stage{Stage.FILE_EXTENSION}"
    stage.export_json(stage_file)

    reopened = Stage()
    reopened.import_json(stage_file)
    node = reopened.root_node.list_children()[0]

    assert node["file"].raw_value == str(path)
    assert node["file"].datatype_id == CoreDatatypes.STRING
