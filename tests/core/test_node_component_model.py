import logging
import pathlib
import typing
from collections import OrderedDict

import pytest
from PySide6 import QtCore

from nyx.api.v1 import (
    Stage,
    CoreNodes,
    CoreNodeComponents,
    NodeComponentValueMask,
    commands,
)
from nyx.utils import file_fn

if typing.TYPE_CHECKING:
    from nyx.plugins.core.nodes.action import ActionNode

LOGGER = logging.getLogger(__name__)


def test_node_components_model_serialize(
    output_dir: pathlib.Path, request: pytest.FixtureRequest
):
    export_path = output_dir / f"{request.node.name}{Stage.FILE_EXTENSION}"
    stage = Stage()
    create_node_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.EMPTY
    )
    stage.push_command(create_node_command)
    node = create_node_command.result_node
    stage.export_json(export_path)

    expected_data = OrderedDict()
    expected_data["components"] = []
    serialized_model = node._components_model.serialize()
    assert serialized_model == expected_data


def test_creating_component_adds_it_to_uuid_map():
    stage = Stage()
    create_node_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.ACTION
    )
    stage.push_command(create_node_command)

    action_node: ActionNode = stage.get_object(create_node_command.result_node.uuid)
    for component in action_node.components_model.list_components():
        assert component.uuid in stage.uuid_map

    add_component_command = commands.AddNodeComponentCommand(
        node=action_node, type_id=CoreNodeComponents.VALUE, name="test_cpnt"
    )
    stage.push_command(add_component_command)

    assert add_component_command.result_component.uuid in stage.uuid_map


def test_removing_component_removes_it_from_uuid_map():
    stage = Stage()
    create_node_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.ACTION
    )
    stage.push_command(create_node_command)

    action_node: ActionNode = stage.get_object(create_node_command.result_node.uuid)
    for component in action_node.components_model.list_components():
        assert component.uuid in stage.uuid_map

    add_component_command = commands.AddNodeComponentCommand(
        node=action_node, type_id=CoreNodeComponents.VALUE, name="test_cpnt"
    )
    stage.push_command(add_component_command)

    resulting_uuid = add_component_command.result_component.uuid
    assert resulting_uuid in stage.uuid_map

    delete_component_command = commands.DeleteNodeComponentCommand(
        node=action_node, component_names=[add_component_command.result_component.name]
    )
    stage.push_command(delete_component_command)

    assert resulting_uuid not in stage.uuid_map

    stage.undo_stack.undo()
    assert resulting_uuid in stage.uuid_map, f"UUID_MAP: {stage.uuid_map}"


def test_attempting_to_remove_builtin_cpnt_raises_value_error():
    stage = Stage()
    create_node_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.BRANCH
    )
    stage.push_command(create_node_command)
    node = create_node_command.result_node

    old_cpnt_count = node.components_model.rowCount()
    for builtin_cpnt in node.components_model.list_components():
        with pytest.raises(ValueError, match="Can't remove builtin component"):
            node.components_model.remove_component(builtin_cpnt.uuid)
    assert old_cpnt_count == node.components_model.rowCount()


def test_importing_node_with_extra_components_gives_correct_values(
    output_dir: pathlib.Path, request: pytest.FixtureRequest
):
    export_path = output_dir / f"{request.node.name}{Stage.FILE_EXTENSION}"

    test_cpnt_name = "test_cpnt"
    test_cpnt_value = "5"

    stage = Stage()
    create_node_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.BRANCH
    )
    stage.push_command(create_node_command)
    node = create_node_command.result_node

    add_cpnt_command = commands.AddNodeComponentCommand(
        node=node, type_id=CoreNodeComponents.VALUE, name=test_cpnt_name
    )
    stage.push_command(add_cpnt_command)
    node[test_cpnt_name].push_value(test_cpnt_value)

    serialized_node = node.serialize()
    file_fn.write_json(export_path, serialized_node)

    other_stage = Stage()
    paste_command = commands.PasteNodesCommand(
        stage=other_stage, serialize_nodes=[serialized_node], position=QtCore.QPointF()
    )
    other_stage.push_command(paste_command)
    pasted_node = paste_command.pasted_nodes[0]

    assert pasted_node[test_cpnt_name] is not None
    assert (
        pasted_node[test_cpnt_name].pull_value(value_mask=NodeComponentValueMask.RAW)
        == test_cpnt_value
    )
    assert pasted_node[test_cpnt_name].pull_value(
        value_mask=NodeComponentValueMask.EVAL
    ) == int(test_cpnt_value)
