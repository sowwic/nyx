from nyx.api.v1 import (
    Node,
    Stage,
    NodeComponent,
    commands,
    CoreNodes,
    CoreNodeComponents,
)
from nyx.core.plugin_subsystem.content_protocol import PluginContent


def test_init_base_component():
    cpnt = NodeComponent()
    assert cpnt.name == NodeComponent.DEFAULT_NAME
    assert cpnt.is_active is True
    assert isinstance(cpnt, PluginContent)


def test_add_base_component_to_node():
    stage = Stage()
    node = Node("test")
    component = NodeComponent()
    node.add_component(component)
    stage.add_node(node)

    assert component.as_path() == node.cached_path.with_suffix(f".{component.name}")


def test_component_name_indexing():
    stage = Stage()
    node = Node("test")
    stage.add_node(node)

    test_name = "test"
    component1 = NodeComponent(name=test_name)
    component2 = NodeComponent(name=test_name)

    node.add_component(component1)
    node.add_component(component2)

    assert len(node.components_model.list_components()) == 2
    assert component1.name == test_name
    assert component2.name == test_name + "1"


def test_serialize():
    """Check that serialized data matches components data"""
    stage = Stage()
    create_node_command = commands.CreateNodeCommand(
        stage=stage, node_type_id=CoreNodes.ACTION
    )
    stage.push_command(create_node_command)

    flow_component = next(
        create_node_command.result_node.components_model.find_components_of_type(
            CoreNodeComponents.FLOW
        )
    )
    data = flow_component.serialize()

    assert data["type_id"] == flow_component.TYPE_ID
    assert data["name"] == flow_component.name
    assert data["value"] == flow_component.value
    assert data["is_active"] == flow_component.is_active
    assert data["is_readable"] == flow_component.is_readable
    assert data["is_writable"] == flow_component.is_writable


def test_serialize_deserialize():
    """Check cycle of serialization-deserialization"""
    stage = Stage()
    create_node_command = commands.CreateNodeCommand(
        stage=stage, node_type_id=CoreNodes.ACTION
    )
    stage.push_command(create_node_command)

    flow_component = next(
        create_node_command.result_node.components_model.find_components_of_type(
            CoreNodeComponents.FLOW
        )
    )
    flow_component.value = "/stage/test"
    flow_component.is_readable = False
    flow_component.is_active = False
    data = flow_component.serialize()

    new_flow_component = (
        create_node_command.result_node.components_model.create_component(
            CoreNodeComponents.FLOW
        )
    )
    create_node_command.result_node.add_component(new_flow_component)
    new_flow_component.deserialize(data)

    assert str(new_flow_component.value) == flow_component.value
    assert new_flow_component.is_active == flow_component.is_active
    assert new_flow_component.is_readable == flow_component.is_readable
    assert new_flow_component.is_writable == flow_component.is_writable
