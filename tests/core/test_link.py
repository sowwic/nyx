import pytest
import pathlib

from nyx.api.v1 import Stage, Node, NodeComponent, CoreNodes, Link, LinkLike, commands


def test_link_creation():
    stage = Stage()
    node1_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.ACTION)
    node2_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.ACTION)

    stage.push_command(node1_command)
    stage.push_command(node2_command)

    link = Link(
        stage=stage,
        source=node1_command.result_node["flow"].uuid,
        target=node2_command.result_node["flow"].uuid,
    )

    assert link.uuid not in stage.uuid_map
    stage.register_link(link)
    assert link.uuid in stage.uuid_map
    assert link.source_component is node1_command.result_node["flow"]
    assert link.target_component is node2_command.result_node["flow"]


def test_link_serialization(output_dir: pathlib.Path, request: pytest.FixtureRequest):
    stage = Stage()
    export_path = output_dir / f"{request.node.name}{stage.FILE_EXTENSION}"
    node1_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.ACTION)
    node2_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.ACTION)

    stage.push_command(node1_command)
    stage.push_command(node2_command)

    link = Link(
        stage=stage,
        source=node1_command.result_node["flow"].uuid,
        target=node2_command.result_node["flow"].uuid,
    )

    assert link.uuid not in stage.uuid_map
    stage.register_link(link)

    stage.export_json(export_path)
