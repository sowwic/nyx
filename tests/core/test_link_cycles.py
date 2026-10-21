import pytest

from nyx.api.v1 import CoreNodes, Stage, commands, exceptions


def make_node(stage, name):
    command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.EMPTY, name=name)
    stage.push_command(command)
    return command.result_node


def add_values(stage, node, *names):
    """Add value components that can be linked in both directions."""
    components = []
    for name in names:
        command = commands.AddNodeComponentCommand(
            node=node, type_id="core:value", name=name
        )
        stage.push_command(command)
        component = command.result_component
        component.readable = True
        component.writable = True
        components.append(component)
    return components


def make_node_of(stage, type_id, name):
    command = commands.CreateNodeCommand(stage=stage, type_id=type_id, name=name)
    stage.push_command(command)
    return command.result_node


@pytest.fixture
def two_nodes():
    stage = Stage()
    node_a = make_node(stage, "a")
    node_b = make_node(stage, "b")
    a1, a2 = add_values(stage, node_a, "value1", "value2")
    b1, b2 = add_values(stage, node_b, "value1", "value2")
    return stage, (a1, a2), (b1, b2)


def test_link_back_between_the_same_components_is_rejected(two_nodes):
    stage, (a1, _), (b1, _) = two_nodes
    stage.link_components(a1, b1)

    with pytest.raises(exceptions.NodeComponentLinkError, match="cycle"):
        stage.link_components(b1, a1)
    assert not a1.input_links


def test_link_back_between_other_components_of_the_nodes_is_rejected(two_nodes):
    stage, (a1, _), (b1, b2) = two_nodes
    stage.link_components(a1, b1)

    with pytest.raises(exceptions.NodeComponentLinkError, match="cycle"):
        stage.link_components(b2, a1)
    assert not a1.input_links


def test_cycle_through_a_third_node_is_rejected(two_nodes):
    stage, (a1, a2), (b1, b2) = two_nodes
    node_c = make_node(stage, "c")
    (c1,) = add_values(stage, node_c, "value1")
    stage.link_components(a1, b1)
    stage.link_components(b2, c1)

    with pytest.raises(exceptions.NodeComponentLinkError, match="cycle"):
        stage.link_components(c1, a2)


def test_chains_without_a_cycle_are_allowed(two_nodes):
    stage, (a1, a2), (b1, b2) = two_nodes
    stage.link_components(a1, b1)
    stage.link_components(a2, b2)

    assert b1.input_links and b2.input_links


def test_links_inside_of_a_node_are_allowed_unless_they_loop(two_nodes):
    stage, (a1, a2), _ = two_nodes
    stage.link_components(a1, a2)

    with pytest.raises(exceptions.NodeComponentLinkError, match="cycle"):
        stage.link_components(a2, a1)


def test_component_can_not_be_linked_to_itself(two_nodes):
    stage, (a1, _), _ = two_nodes

    with pytest.raises(exceptions.NodeComponentLinkError, match="cycle"):
        stage.link_components(a1, a1)


def test_flow_links_can_not_loop_back():
    stage = Stage()
    nodes = [make_node(stage, name) for name in ("a", "b", "c")]
    flows = []
    for node in nodes:
        command = commands.AddNodeComponentCommand(node=node, type_id="core:flow")
        stage.push_command(command)
        command.result_component.readable = True
        command.result_component.writable = True
        flows.append(command.result_component)
    flow_a, flow_b, flow_c = flows
    stage.link_components(flow_a, flow_b)
    stage.link_components(flow_b, flow_c)

    # Flow outputs take a single link, so only the end of the chain can loop back
    with pytest.raises(exceptions.NodeComponentLinkError, match="cycle"):
        stage.link_components(flow_c, flow_a)


def test_loop_nodes_repeat_their_body_without_a_cycle():
    stage = Stage()
    start = make_node_of(stage, CoreNodes.FLOW_START, "start")
    loop = make_node_of(stage, CoreNodes.FOR_LOOP, "loop")
    body = make_node_of(stage, CoreNodes.ACTION, "body")
    start["flow"] >> loop["flow"]
    loop["loop_body"] >> body["flow"]
    loop["first_index"].push_value(0)
    loop["last_index"].push_value(2)

    stage.crawler.start()

    names = [path.rsplit("/", 1)[-1] for path in stage.crawler.execution_paths_stack]
    assert names.count("body") == 3


def test_link_command_rejects_a_cycle(two_nodes):
    stage, (a1, _), (b1, _) = two_nodes
    stage.push_command(
        commands.LinkNodeComponentsCommand(stage=stage, source=a1, target=b1)
    )

    with pytest.raises(exceptions.NodeComponentLinkError, match="cycle"):
        stage.push_command(
            commands.LinkNodeComponentsCommand(stage=stage, source=b1, target=a1)
        )
    assert not a1.input_links


def test_editor_does_not_offer_links_that_make_a_cycle(two_nodes):
    from nyx.editor.graphics.graphics_stage import GraphicsStage

    stage, (a1, _), (b1, b2) = two_nodes
    stage.link_components(a1, b1)

    assert not GraphicsStage.can_link(b1, a1)
    assert not GraphicsStage.can_link(b2, a1)
    assert GraphicsStage.can_link(a1, b2)


def test_undoing_and_redoing_a_link_keeps_working(two_nodes):
    stage, (a1, _), (b1, _) = two_nodes
    stage.push_command(
        commands.LinkNodeComponentsCommand(stage=stage, source=a1, target=b1)
    )

    stage.undo_stack.undo()
    assert not b1.input_links
    assert not stage.would_link_create_cycle(b1, a1)

    stage.undo_stack.redo()
    assert b1.input_links
    assert stage.would_link_create_cycle(b1, a1)
