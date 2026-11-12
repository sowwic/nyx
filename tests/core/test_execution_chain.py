from nyx.api.v1 import Stage, CoreNodes, Link, commands
from nyx.core.execution_chain import ExecutionChain
from stage_helpers import create_node


def connect(stage: Stage, source, target, source_name="flow", target_name="flow"):
    stage.push_command(
        commands.LinkNodeComponentsCommand(
            stage=stage, source=source[source_name], target=target[target_name]
        )
    )


def chain_of(stage: Stage, scope=None) -> set:
    return set(ExecutionChain.find_node_uuids(scope or stage.root_node))


def test_chain_follows_the_flow_from_the_flow_start():
    stage = Stage()
    start = create_node(stage, CoreNodes.FLOW_START)
    first = create_node(stage, CoreNodes.ACTION)
    second = create_node(stage, CoreNodes.ACTION)
    connect(stage, start, first)
    connect(stage, first, second)

    assert chain_of(stage) == {start.uuid, first.uuid, second.uuid}


def test_node_without_a_flow_path_is_not_on_the_chain():
    stage = Stage()
    start = create_node(stage, CoreNodes.FLOW_START)
    linked = create_node(stage, CoreNodes.ACTION)
    loose = create_node(stage, CoreNodes.ACTION)
    connect(stage, start, linked)

    assert loose.uuid not in chain_of(stage)
    assert linked.uuid in chain_of(stage)


def test_scope_without_a_flow_start_has_an_empty_chain():
    stage = Stage()
    create_node(stage, CoreNodes.ACTION)

    assert chain_of(stage) == set()


def test_only_the_active_output_of_a_branch_is_on_the_chain():
    stage = Stage()
    start = create_node(stage, CoreNodes.FLOW_START)
    branch = create_node(stage, CoreNodes.BRANCH)
    on_true = create_node(stage, CoreNodes.ACTION)
    on_false = create_node(stage, CoreNodes.ACTION)
    connect(stage, start, branch)
    connect(stage, branch, on_true, source_name="true")
    connect(stage, branch, on_false, source_name="false")

    # The condition is true by default, so only the true output is active.
    assert on_true.uuid in chain_of(stage)
    assert on_false.uuid not in chain_of(stage)

    branch["condition"].push_value(False)

    assert on_false.uuid in chain_of(stage)
    assert on_true.uuid not in chain_of(stage)


def test_inactive_flow_output_does_not_lead_on():
    stage = Stage()
    start = create_node(stage, CoreNodes.FLOW_START)
    branch = create_node(stage, CoreNodes.BRANCH)
    on_false = create_node(stage, CoreNodes.ACTION)
    connect(stage, start, branch)
    connect(stage, branch, on_false, source_name="false")
    branch["false"].is_active = False

    assert on_false.uuid not in chain_of(stage)


def test_cycle_does_not_loop_forever():
    stage = Stage()
    start = create_node(stage, CoreNodes.FLOW_START)
    first = create_node(stage, CoreNodes.ACTION)
    second = create_node(stage, CoreNodes.ACTION)
    # A flow input takes one link, so a cycle can't be entered from the start.
    # Linking components refuses cycles, a stage loaded from a file may still have one.
    connect(stage, first, second)
    stage.register_link(Link(stage, second["flow"].uuid, first["flow"].uuid))

    assert chain_of(stage) == {start.uuid}


def test_scope_inside_a_node_off_the_chain_is_not_reached():
    stage = Stage()
    start = create_node(stage, CoreNodes.FLOW_START)
    reached = create_node(stage, CoreNodes.ACTION, name="reached")
    unreached = create_node(stage, CoreNodes.ACTION, name="unreached")
    connect(stage, start, reached)
    inner_start = create_node(stage, CoreNodes.FLOW_START, parent=reached)
    unreached_start = create_node(stage, CoreNodes.FLOW_START, parent=unreached)

    assert chain_of(stage, reached) == {inner_start.uuid}
    assert chain_of(stage, unreached) == set()
    assert unreached_start.uuid not in chain_of(stage, unreached)
