import pytest

from nyx.api.v1 import CoreNodes, NodeExecutionContext, Stage, commands
from nyx.stdlib.nodes.log import LogNode


class Marker:
    """Something a node provides to its children."""


@pytest.fixture
def context():
    return NodeExecutionContext(stage=None)


def test_find_looks_from_the_innermost_scope_outwards(context):
    outer, inner = Marker(), Marker()
    context.provide(outer)
    context.push_scope(object())
    assert context.find(Marker) is outer

    context.provide(inner)

    assert context.find(Marker) is inner
    context.pop_scope()
    assert context.find(Marker) is outer


def test_find_matches_subclasses_and_returns_none_without_a_match(context):
    class Special(Marker):
        pass

    assert context.find(Marker) is None
    special = Special()
    context.provide(special)

    assert context.find(Marker) is special
    assert context.find(Special) is special
    assert context.find(int) is None


def test_require_raises_when_nothing_is_provided(context):
    with pytest.raises(LookupError, match="Marker"):
        context.require(Marker)

    marker = Marker()
    context.provide(marker)
    assert context.require(Marker) is marker


def test_services_are_gone_after_their_scope_is_closed(context):
    context.push_scope(object())
    context.provide(Marker())
    context.pop_scope()

    assert context.find(Marker) is None
    assert context.scope_depth == 0


def test_cleanups_run_most_recent_first_when_the_scope_closes(context):
    events = []
    context.push_scope(object())
    context.add_cleanup(lambda: events.append("first"))
    context.add_cleanup(lambda: events.append("second"))
    assert events == []

    context.pop_scope()

    assert events == ["second", "first"]


def test_failing_cleanup_does_not_keep_the_others_from_running(context):
    events = []

    def fail():
        raise RuntimeError("cleanup failure")

    context.push_scope(object())
    context.add_cleanup(lambda: events.append("ran"))
    context.add_cleanup(fail)

    context.pop_scope()

    assert events == ["ran"]


def test_unwind_closes_every_scope_and_leaves_a_usable_context(context):
    events = []
    context.add_cleanup(lambda: events.append("root"))
    context.push_scope(object())
    context.add_cleanup(lambda: events.append("inner"))

    context.unwind()

    assert events == ["inner", "root"]
    assert context.scope_depth == 0
    context.provide(Marker())
    assert context.find(Marker) is not None


def test_popping_the_root_scope_is_an_error(context):
    with pytest.raises(RuntimeError):
        context.pop_scope()


def _build_stage():
    """Stage with `outer/inner` log nodes and a following `after` log node.

    flow_start -> outer -> after, and inside outer: flow_start -> inner.
    """
    stage = Stage()

    def create(type_id, parent_node=None):
        command = commands.CreateNodeCommand(
            stage=stage, type_id=type_id, parent_node=parent_node
        )
        stage.push_command(command)
        return command.result_node

    flow_start = create(CoreNodes.FLOW_START)
    outer = create(CoreNodes.LOG)
    after = create(CoreNodes.LOG)
    create(CoreNodes.FLOW_START, parent_node=outer.path)
    inner = create(CoreNodes.LOG, parent_node=outer.path)

    flow_start["flow"] >> outer["flow"]
    outer["flow"] >> after["flow"]
    outer.find_flow_start_node()["flow"] >> inner["flow"]
    return stage, outer, inner, after


def test_children_find_what_their_parent_provides_but_siblings_do_not(monkeypatch):
    stage, outer, inner, after = _build_stage()
    marker = Marker()
    events = []

    def enter_scope(node, context):
        if node is outer:
            events.append("enter outer")
            context.provide(marker)
            context.add_cleanup(lambda: events.append("cleanup outer"))

    def execute(node):
        found = node.stage.crawler.context.find(Marker)
        events.append((node.path.as_posix(), found))

    monkeypatch.setattr(LogNode, "enter_scope", enter_scope)
    monkeypatch.setattr(LogNode, "execute", execute)

    stage.crawler.start()

    assert events == [
        (outer.path.as_posix(), None),
        "enter outer",
        (inner.path.as_posix(), marker),
        "cleanup outer",
        (after.path.as_posix(), None),
    ]
    assert stage.crawler.context.scope_depth == 0


def test_scope_of_a_node_executing_after_its_children_covers_the_children(monkeypatch):
    stage, outer, inner, _ = _build_stage()
    events = []
    monkeypatch.setattr(
        LogNode,
        "get_type_execution_order",
        classmethod(lambda cls: _after_children_for(cls)),
    )

    def enter_scope(node, context):
        if node is outer:
            events.append("enter outer")
            context.add_cleanup(lambda: events.append("cleanup outer"))

    monkeypatch.setattr(LogNode, "enter_scope", enter_scope)
    monkeypatch.setattr(
        LogNode, "execute", lambda node: events.append(f"execute {node.path.as_posix()}")
    )

    stage.crawler.start()

    assert events.index("enter outer") < events.index(f"execute {inner.path.as_posix()}")
    assert events.index(f"execute {inner.path.as_posix()}") < events.index(
        "cleanup outer"
    )
    assert events.index("cleanup outer") < events.index(
        f"execute {outer.path.as_posix()}"
    )


def _after_children_for(cls):
    from nyx.static.enums import NodeExecutionOrderFlag

    return NodeExecutionOrderFlag.AFTER_CHILDREN


def test_cleanups_run_when_a_child_fails(monkeypatch):
    stage, outer, inner, after = _build_stage()
    events = []

    def enter_scope(node, context):
        if node is outer:
            context.add_cleanup(lambda: events.append("cleanup outer"))

    def execute(node):
        if node is inner:
            raise RuntimeError("child failed")
        events.append(f"execute {node.path.as_posix()}")

    monkeypatch.setattr(LogNode, "enter_scope", enter_scope)
    monkeypatch.setattr(LogNode, "execute", execute)

    with pytest.raises(RuntimeError, match="child failed"):
        stage.crawler.start()

    assert events == [f"execute {outer.path.as_posix()}", "cleanup outer"]
    assert stage.crawler.context.scope_depth == 0


def test_every_crawl_gets_a_fresh_context():
    stage, *_ = _build_stage()

    stage.crawler.start()
    first = stage.crawler.context
    first.provide(Marker())
    stage.crawler.start()

    assert stage.crawler.context is not first
    assert stage.crawler.context.find(Marker) is None


def test_nodes_without_scope_hook_are_unaffected():
    stage, outer, inner, after = _build_stage()

    stage.crawler.start()

    assert stage.crawler.visited_node_paths[-1] == after.path.as_posix()
    assert stage.crawler.context.scope_depth == 0
