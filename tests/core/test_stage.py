import pathlib
from collections import OrderedDict
import logging
import pytest

from nyx.utils import file_fn
from nyx.api.v1 import Stage, CoreNodes, commands

LOGGER = logging.getLogger(__name__)


def test_stage_create_empty():
    stage = Stage()
    assert stage.undo_stack.isClean()
    assert stage.root_node.list_children() == []


def test_stage_export_import_json(
    output_dir: pathlib.Path, request: pytest.FixtureRequest
):
    stage = Stage()
    export_path = output_dir / f"{request.node.name}{stage.FILE_EXTENSION}"
    # Add nodes
    for _ in range(3):
        create_node_command = commands.CreateNodeCommand(
            stage=stage, type_id=CoreNodes.EMPTY
        )
        stage.push_command(create_node_command)
        base_node = create_node_command.result_node
        for _ in range(3):
            create_node_command = commands.CreateNodeCommand(
                stage=stage,
                type_id=CoreNodes.EMPTY,
                name="child_node",
                parent_node=base_node,
            )
            stage.push_command(create_node_command)
            child_node = create_node_command.result_node
            for _ in range(2):
                create_node_command = commands.CreateNodeCommand(
                    stage=stage,
                    type_id=CoreNodes.EMPTY,
                    name="leaf_node",
                    parent_node=child_node,
                )
                stage.push_command(create_node_command)

    stage.export_json(export_path)
    assert export_path.is_file()

    # Import data and compare with stage serialized
    assert stage.root_node.serialize() == file_fn.load_json(
        export_path, object_pairs_hook=OrderedDict
    )


def test_stage_deserialize(output_dir: pathlib.Path, request: pytest.FixtureRequest):
    stage = Stage()
    export_path = output_dir / f"{request.node.name}_export{stage.FILE_EXTENSION}"
    export_path2 = output_dir / f"{request.node.name}_check{stage.FILE_EXTENSION}"
    # Add nodes
    for _ in range(3):
        create_node_command = commands.CreateNodeCommand(
            stage=stage, type_id=CoreNodes.EMPTY
        )
        stage.push_command(create_node_command)
        base_node = create_node_command.result_node
        for _ in range(3):
            create_node_command = commands.CreateNodeCommand(
                stage=stage,
                type_id=CoreNodes.EMPTY,
                name="child_node",
                parent_node=base_node,
            )
            stage.push_command(create_node_command)
            child_node = create_node_command.result_node
            for _ in range(2):
                create_node_command = commands.CreateNodeCommand(
                    stage=stage,
                    type_id=CoreNodes.EMPTY,
                    name="leaf_node",
                    parent_node=child_node,
                )
                stage.push_command(create_node_command)

    stage.export_json(export_path)

    stage2 = Stage()
    stage2.import_json(export_path)
    stage2.export_json(export_path2)

    assert stage2.root_node.serialize() == stage.root_node.serialize()


def test_stage_deserialize_plugin_nodes(
    output_dir: pathlib.Path, request: pytest.FixtureRequest
):
    stage = Stage()
    export_path = output_dir / f"{request.node.name}_export{stage.FILE_EXTENSION}"
    export_path2 = output_dir / f"{request.node.name}_check{stage.FILE_EXTENSION}"
    # TODO: add components to nodes
    for _ in range(3):
        base_node_create_command = commands.CreateNodeCommand(
            stage=stage, type_id=CoreNodes.ACTION
        )
        stage.push_command(base_node_create_command)
        for _ in range(3):
            child_node_create_command = commands.CreateNodeCommand(
                stage=stage,
                type_id=CoreNodes.ACTION,
                parent_node=base_node_create_command.result_node.uuid,
            )
            stage.push_command(child_node_create_command)
            for _ in range(2):
                deep_child_create_command = commands.CreateNodeCommand(
                    stage=stage,
                    type_id=CoreNodes.BRANCH,
                    parent_node=child_node_create_command.result_node.uuid,
                )
                stage.push_command(deep_child_create_command)

    stage.export_json(export_path)

    stage2 = Stage()
    stage2.import_json(export_path)

    last_imported_deep_child = stage2.get_object(
        deep_child_create_command.result_node.uuid
    )
    last_imported_child_node = stage2.get_object(
        child_node_create_command.result_node.uuid
    )
    last_imported_base_node = stage2.get_object(
        base_node_create_command.result_node.uuid
    )

    assert last_imported_deep_child.get_type_id() == CoreNodes.BRANCH
    assert last_imported_child_node.get_type_id() == CoreNodes.ACTION
    assert last_imported_base_node.get_type_id() == CoreNodes.ACTION

    stage2.export_json(export_path2)

    assert stage2.root_node.serialize() == stage.root_node.serialize()


def test_attempt_deleting_locked_node_raises_error():
    stage = Stage()
    with pytest.raises(RuntimeError, match="locked node"):
        stage.delete_node(stage.root_node)


# TODO Update after component are added
def test_stage_export_import_with_connections(
    output_dir: pathlib.Path, request: pytest.FixtureRequest
):
    export_path = output_dir / f"{request.node.name}{Stage.FILE_EXTENSION}"

    stage1 = Stage()
    node1_create_command = commands.CreateNodeCommand(stage1, type_id=CoreNodes.ACTION)
    node2_create_command = commands.CreateNodeCommand(stage1, type_id=CoreNodes.ACTION)

    stage1.push_command(node1_create_command)
    stage1.push_command(node2_create_command)

    node1 = node1_create_command.result_node
    node2 = node2_create_command.result_node

    # Connections
    node1["flow"].value = node2.path

    stage1.export_json(export_path)

    stage2 = Stage()
    stage2.import_json(export_path)

    assert stage1.root_node.serialize() == stage2.root_node.serialize()


def test_stage_convert_to_node():
    # Original stage
    stage = Stage()

    node1_create_command = commands.CreateNodeCommand(stage=stage)
    node2_create_command = commands.CreateNodeCommand(stage=stage)
    stage.push_command(node1_create_command)
    stage.push_command(node2_create_command)

    # Final stage
    main_stage = Stage()
    main_node_create_command = commands.CreateNodeCommand(stage=main_stage)
    main_stage.push_command(main_node_create_command)
    stage_node = main_node_create_command.result_node

    serialized_stage_node = stage.root_node.serialize()

    stage_node.deserialize(serialized_node=serialized_stage_node, node=stage_node)
    LOGGER.debug(main_stage.describe())

    new_child_paths = [
        stage_node.path / node1_create_command.result_node.path.name,
        stage_node.path / node2_create_command.result_node.path.name,
    ]
    assert stage_node.name == stage.root_node.name
    assert stage_node.list_children_paths() == new_child_paths
