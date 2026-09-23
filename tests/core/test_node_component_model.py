import logging
import pathlib
import typing
from collections import OrderedDict

import pytest
from nyx.api.v1 import Node, Stage, CoreNodes, CoreNodeComponents, commands

if typing.TYPE_CHECKING:
    from nyx.plugins.core.nodes.action import ActionNode

LOGGER = logging.getLogger(__name__)


def test_node_components_model_serialize(
    output_dir: pathlib.Path, request: pytest.FixtureRequest
):
    export_path = output_dir / f"{request.node.name}{Stage.FILE_EXTENSION}"
    stage = Stage()
    node = Node()
    stage.add_node(node)
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
        node=action_node,
        name=add_component_command.result_component.name,
    )
    stage.push_command(delete_component_command)

    assert resulting_uuid not in stage.uuid_map

    stage.undo_stack.undo()
    assert resulting_uuid in stage.uuid_map, f"UUID_MAP: {stage.uuid_map}"
