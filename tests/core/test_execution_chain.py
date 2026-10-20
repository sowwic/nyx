from nyx.api.v1 import Stage, CoreNodes, commands
from nyx.core.execution_chain import ExecutionChain


def make_node(stage: Stage, type_id: str, parent=None, name: str | None = None):
    command = commands.CreateNodeCommand(
        stage=stage, type_id=type_id, parent_node=parent, name=name
    )
    stage.push_command(command)
    return command.result_node


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
    start = make_node(stage, CoreNodes.FLOW_START)
    first = make_node(stage, CoreNodes.ACTION)
    second = make_node(stage, CoreNodes.ACTION)
    connect(stage, start, first)
    connect(stage, first, second)

    assert chain_of(stage) == {start.uuid, first.uuid, second.uuid}


def test_node_without_a_flow_path_is_not_on_the_chain():
    stage = Stage()
    start = make_node(stage, CoreNodes.FLOW_START)
    linked = make_node(stage, CoreNodes.ACTION)
    loose = make_node(stage, CoreNodes.ACTION)
    connect(stage, start, linked)

    assert loose.uuid not in chain_of(stage)
    assert linked.uuid in chain_of(stage)


def test_scope_without_a_flow_start_has_an_empty_chain():
    stage = Stage()
    make_node(stage, CoreNodes.ACTION)

    assert chain_of(stage) == set()


def test_both_outputs_of_a_branch_are_on_the_chain():
    stage = Stage()
    start = make_node(stage, CoreNodes.FLOW_START)
    branch = make_node(stage, CoreNodes.BRANCH)
    on_true = make_node(stage, CoreNodes.ACTION)
    on_false = make_node(stage, CoreNodes.ACTION)
    connect(stage, start, branch)
    connect(stage, branch, on_true, source_name="true")
    connect(stage, branch, on_false, source_name="false")

    assert {on_true.uuid, on_false.uuid} <= chain_of(stage)


def test_inactive_branch_output_is_still_on_the_chain():
    stage = Stage()
    start = make_node(stage, CoreNodes.FLOW_START)
    branch = make_node(stage, CoreNodes.BRANCH)
    on_false = make_node(stage, CoreNodes.ACTION)
    connect(stage, start, branch)
    connect(stage, branch, on_false, source_name="false")
    branch["false"].is_active = False

    assert on_false.uuid in chain_of(stage)


def test_cycle_does_not_loop_forever():
    stage = Stage()
    start = make_node(stage, CoreNodes.FLOW_START)
    first = make_node(stage, CoreNodes.ACTION)
    second = make_node(stage, CoreNodes.ACTION)
    # A flow input takes one link, so a cycle can't be entered from the start
    connect(stage, first, second)
    connect(stage, second, first)

    assert chain_of(stage) == {start.uuid}


def test_scope_inside_a_node_off_the_chain_is_not_reached():
    stage = Stage()
    start = make_node(stage, CoreNodes.FLOW_START)
    reached = make_node(stage, CoreNodes.ACTION, name="reached")
    unreached = make_node(stage, CoreNodes.ACTION, name="unreached")
    connect(stage, start, reached)
    inner_start = make_node(stage, CoreNodes.FLOW_START, parent=reached)
    unreached_start = make_node(stage, CoreNodes.FLOW_START, parent=unreached)

    assert chain_of(stage, reached) == {inner_start.uuid}
    assert chain_of(stage, unreached) == set()
    assert unreached_start.uuid not in chain_of(stage, unreached)
