import pytest

from nyx.api.v1 import (
    Stage,
    Link,
    CoreNodes,
    CoreNodeComponents,
    NodeComponentLike,
    commands,
    exceptions,
)


def make_node(stage: Stage, type_id: str):
    command = commands.CreateNodeCommand(stage=stage, type_id=type_id)
    stage.push_command(command)
    return command.result_node


def make_link(stage: Stage, source: NodeComponentLike, target: NodeComponentLike):
    command = commands.LinkNodeComponentsCommand(
        stage=stage, source=source, target=target
    )
    stage.push_command(command)
    return command


def assert_link_state(stage, link_command, source_node, target_node, *, linked):
    link_uuid = link_command.result_link_uuid
    assert Link.is_registered(stage, link_uuid) is linked
    assert (link_uuid in source_node["flow"].output_links_uuids) is linked
    assert (link_uuid in target_node["flow"].links_uuids) is linked
    assert (link_uuid in target_node["flow"].input_links_uuids) is linked


def test_single_link_push():
    stage = Stage()
    node1_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.ACTION)
    node2_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.ACTION)

    stage.push_command(node1_command)
    stage.push_command(node2_command)

    link_command = commands.LinkNodeComponentsCommand(
        stage=stage,
        source=node1_command.result_node["flow"],
        target=node2_command.result_node["flow"],
    )
    stage.push_command(link_command)

    assert Link.is_registered(stage, link_command.result_link_uuid)


def test_linking_with_existing_link_restores_original_on_undo():
    stage = Stage()
    node1 = make_node(stage=stage, type_id=CoreNodes.ACTION)
    node2 = make_node(stage=stage, type_id=CoreNodes.ACTION)
    node3 = make_node(stage=stage, type_id=CoreNodes.ACTION)

    # Create link node1.flow >> node2.flow
    link1_command = make_link(stage, node1["flow"], node2["flow"])
    assert_link_state(stage, link1_command, node1, node2, linked=True)

    # Create link node3.flow >> node2.flow (should unlink link1)
    link2_command = make_link(stage, node3["flow"], node2["flow"])
    assert_link_state(stage, link1_command, node1, node2, linked=False)
    assert_link_state(stage, link2_command, node3, node2, linked=True)

    # Undo restores link1, removes link2
    stage.undo_stack.undo()
    assert_link_state(stage, link1_command, node1, node2, linked=True)
    assert_link_state(stage, link2_command, node3, node2, linked=False)

    # Redo re-applies link2, removes link1
    stage.undo_stack.redo()
    assert_link_state(stage, link1_command, node1, node2, linked=False)
    assert_link_state(stage, link2_command, node3, node2, linked=True)


def test_linking_to_not_writable_component_raises_link_error():
    stage = Stage()
    node1 = make_node(stage=stage, type_id=CoreNodes.ACTION)
    node2 = make_node(stage=stage, type_id=CoreNodes.FLOW_START)
    node2["flow"].writable = False

    with pytest.raises(
        exceptions.NodeComponentLinkError, match="Not writable component"
    ):
        make_link(stage=stage, source=node1["flow"], target=node2["flow"])


def test_linking_from_not_readable_component_raises_link_error():
    stage = Stage()
    node1 = make_node(stage=stage, type_id=CoreNodes.ACTION)
    node2 = make_node(stage=stage, type_id=CoreNodes.LOG)

    add_cpnt_command = commands.AddNodeComponentCommand(
        node=node1, type_id=CoreNodeComponents.VALUE, name="test_cpnt"
    )
    stage.push_command(add_cpnt_command)

    with pytest.raises(
        exceptions.NodeComponentLinkError, match="Not readable component"
    ):
        make_link(stage=stage, source=node1["test_cpnt"], target=node2["message"])


def test_flow_component_allows_a_single_output_link():
    stage = Stage()
    node1, node2, node3 = (make_node(stage, CoreNodes.ACTION) for _ in range(3))
    assert node1["flow"].single_output

    stage.link_components(node1["flow"], node2["flow"])
    with pytest.raises(exceptions.NodeComponentLinkError, match="single output"):
        stage.link_components(node1["flow"], node3["flow"])
    assert len(node1["flow"].output_links) == 1


def test_value_component_allows_many_output_links():
    stage = Stage()
    node1 = make_node(stage, CoreNodes.ACTION)
    node2, node3 = make_node(stage, CoreNodes.LOG), make_node(stage, CoreNodes.LOG)
    add = commands.AddNodeComponentCommand(
        node=node1, type_id=CoreNodeComponents.VALUE, name="out"
    )
    stage.push_command(add)
    out = add.result_component
    out.readable = True
    assert not out.single_output

    stage.link_components(out, node2["message"])
    stage.link_components(out, node3["message"])
    assert len(out.output_links) == 2


def test_linking_from_a_single_output_component_replaces_its_link_in_one_undo_step():
    stage = Stage()
    node1, node2, node3 = (make_node(stage, CoreNodes.ACTION) for _ in range(3))
    first = make_link(stage, node1["flow"], node2["flow"])
    second = make_link(stage, node1["flow"], node3["flow"])

    assert_link_state(stage, first, node1, node2, linked=False)
    assert_link_state(stage, second, node1, node3, linked=True)
    assert [link.target for link in node1["flow"].output_links] == [node3["flow"].uuid]

    stage.undo_stack.undo()
    assert_link_state(stage, first, node1, node2, linked=True)
    assert_link_state(stage, second, node1, node3, linked=False)

    stage.undo_stack.redo()
    assert_link_state(stage, first, node1, node2, linked=False)
    assert_link_state(stage, second, node1, node3, linked=True)
