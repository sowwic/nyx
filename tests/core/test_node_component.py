from nyx.api.v1 import (
    Stage,
    NodeComponent,
    commands,
    CoreNodes,
    CoreNodeComponents,
    NodeDeserializationContext,
    NodeComponentFlag,
)
from nyx.core.protocols.registry_entry import IRegistryEntry


def test_init_base_component():
    stage = Stage()
    create_node_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.EMPTY
    )
    stage.push_command(create_node_command)
    node = create_node_command.result_node

    cpnt_command = commands.AddNodeComponentCommand(
        node=node, type_id=CoreNodeComponents.VALUE
    )
    stage.push_command(cpnt_command)

    cpnt = cpnt_command.result_component
    assert cpnt.name == cpnt.DEFAULT_NAME
    assert cpnt.is_active is True
    assert isinstance(cpnt, IRegistryEntry)


def test_component_name_indexing():
    stage = Stage()
    create_node_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.EMPTY
    )
    stage.push_command(create_node_command)
    node = create_node_command.result_node

    test_name = "test_cpnt"
    cpnt1_command = commands.AddNodeComponentCommand(
        node=node, type_id=CoreNodeComponents.VALUE, name=test_name
    )
    cpnt2_command = commands.AddNodeComponentCommand(
        node=node, type_id=CoreNodeComponents.VALUE, name=test_name
    )
    stage.push_command(cpnt1_command, cpnt2_command)

    component1 = cpnt1_command.result_component
    component2 = cpnt2_command.result_component

    assert len(node.components_model.list_components()) == 2
    assert component1.name == test_name
    assert component2.name == test_name + "1"


def test_serialize():
    """Check that serialized data matches components data"""
    stage = Stage()
    create_node_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.ACTION
    )
    stage.push_command(create_node_command)

    flow_component = next(
        create_node_command.result_node.components_model.find_components_of_type(
            CoreNodeComponents.FLOW
        )
    )
    data = flow_component.serialize()

    assert data["type_id"] == flow_component.get_type_id()
    assert data["name"] == flow_component.name
    assert data["value"] == flow_component.pull_value()
    assert data["is_active"] == flow_component.is_active
    assert data["flags"] == flow_component.component_flags


def test_serialize_deserialize():
    """Check cycle of serialization-deserialization"""
    stage = Stage()
    create_node_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.ACTION
    )
    stage.push_command(create_node_command)

    flow_component = next(
        create_node_command.result_node.components_model.find_components_of_type(
            CoreNodeComponents.FLOW
        )
    )
    flow_component.push_value("/stage/test")
    flow_component.readable = False
    flow_component.is_active = False
    data = flow_component.serialize()

    context = NodeDeserializationContext(
        stage=stage, entry_node=create_node_command.result_node
    )
    new_flow_component = NodeComponent.deserialize(
        data=data, node=create_node_command.result_node, context=context
    )
    create_node_command.result_node.add_component(new_flow_component)

    assert str(new_flow_component.pull_value()) == flow_component.pull_value()
    assert new_flow_component.is_active == flow_component.is_active
    assert new_flow_component.readable == flow_component.readable
    assert new_flow_component.writable == flow_component.writable


def test_deserialized_flow_component_gets_the_enforced_flags():
    stage = Stage()
    create_node_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.ACTION
    )
    stage.push_command(create_node_command)
    node = create_node_command.result_node
    data = node["flow"].serialize()
    # Saved before the flag existed
    data["flags"] = int(
        NodeComponentFlag(data["flags"]) & ~NodeComponentFlag.SINGLE_OUTPUT
    )

    context = NodeDeserializationContext(stage=stage, entry_node=node)
    loaded = NodeComponent.deserialize(data=data, node=node, context=context)

    assert loaded.single_output


def test_rshift_operator():
    stage = Stage()
    create_node1_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.ACTION
    )
    create_node2_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.ACTION
    )
    stage.push_command(create_node1_command)
    stage.push_command(create_node2_command)
    node1 = create_node1_command.result_node
    node2 = create_node2_command.result_node

    link = node1["flow"] >> node2["flow"]

    assert link.source_component is node1["flow"]
    assert link.target_component is node2["flow"]
    assert link.uuid in node1["flow"].links_uuids
    assert link.uuid in node2["flow"].links_uuids


def test_rrshift_operator():
    stage = Stage()
    create_node1_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.ACTION
    )
    create_node2_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.ACTION
    )
    stage.push_command(create_node1_command)
    stage.push_command(create_node2_command)
    node1 = create_node1_command.result_node
    node2 = create_node2_command.result_node

    link = node1["flow"].path >> node2["flow"]
    assert link.source_component is node1["flow"]
    assert link.target_component is node2["flow"]
    assert link.uuid in node1["flow"].links_uuids
    assert link.uuid in node2["flow"].links_uuids


def test_lshift_operator():
    stage = Stage()
    create_node1_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.ACTION
    )
    create_node2_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.ACTION
    )
    stage.push_command(create_node1_command)
    stage.push_command(create_node2_command)
    node1 = create_node1_command.result_node
    node2 = create_node2_command.result_node

    link = node2["flow"] << node1["flow"]
    assert link.source_component is node1["flow"]
    assert link.target_component is node2["flow"]
    assert link.uuid in node1["flow"].links_uuids
    assert link.uuid in node2["flow"].links_uuids


def test_rlshift_operator():
    stage = Stage()
    create_node1_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.ACTION
    )
    create_node2_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.ACTION
    )
    stage.push_command(create_node1_command)
    stage.push_command(create_node2_command)
    node1 = create_node1_command.result_node
    node2 = create_node2_command.result_node

    link = node2["flow"].path << node1["flow"]
    assert link.source_component is node1["flow"]
    assert link.target_component is node2["flow"]
    assert link.uuid in node1["flow"].links_uuids
    assert link.uuid in node2["flow"].links_uuids


def test_linking_notifies_model_of_link_changes():
    from nyx.api.v1 import Stage, CoreNodes, commands

    stage = Stage()
    cmds = [
        commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.ACTION)
        for _ in range(2)
    ]
    for cmd in cmds:
        stage.push_command(cmd)
    a, b = (cmd.result_node for cmd in cmds)
    source, target = a["flow"], b["flow"]

    changes = []
    target.model().dataChanged.connect(lambda *args: changes.append(args[2]))
    link = source >> target
    assert any(target.Roles.INPUT_LINKS in roles for roles in changes)

    changes.clear()
    stage.unregister_link(link)
    assert any(target.Roles.INPUT_LINKS in roles for roles in changes)
    assert target.input_links == []
