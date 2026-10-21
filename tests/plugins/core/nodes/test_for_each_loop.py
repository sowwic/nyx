import pathlib

import pytest

from nyx.api.v1 import Stage, CoreNodes, commands


def make_node(stage, type_id=CoreNodes.ACTION, name=None):
    command = commands.CreateNodeCommand(stage=stage, type_id=type_id, name=name)
    stage.push_command(command)
    return command.result_node


def executed_names(stage):
    return [
        pathlib.PurePosixPath(path).name for path in stage.crawler.execution_paths_stack
    ]


def make_loop_stage(iterable, with_body=True):
    """Build flow_start -> loop, loop_body -> body, completed -> done."""
    stage = Stage()
    start = make_node(stage, CoreNodes.FLOW_START, name="start")
    loop = make_node(stage, CoreNodes.FOR_EACH_LOOP, name="loop")
    body = make_node(stage, name="body")
    done = make_node(stage, name="done")
    loop["iterable"].push_value(iterable)
    start["flow"] >> loop["flow"]
    if with_body:
        loop["loop_body"] >> body["flow"]
    loop["completed"] >> done["flow"]
    return stage, loop


def test_for_each_loop_node_creation():
    stage = Stage()
    loop = make_node(stage, CoreNodes.FOR_EACH_LOOP)

    assert loop.get_type_id() == CoreNodes.FOR_EACH_LOOP
    for name in (
        "flow",
        "iterable",
        "reverse",
        "loop_body",
        "element",
        "index",
        "completed",
    ):
        assert loop[name] is not None
    assert loop.get_self_driven_flow_components() == (loop["loop_body"],)


def test_body_runs_once_per_element_then_completed():
    stage, _ = make_loop_stage([10, 20, 30])

    stage.crawler.start()

    assert executed_names(stage) == (
        ["stage", "start"] + ["body"] * 3 + ["loop", "done"]
    )


def test_element_and_index_hold_the_last_iteration_values():
    stage, loop = make_loop_stage(["a", "b", "c"])

    stage.crawler.start()

    assert loop["index"].pull_value() == 2
    assert loop["element"].pull_value() == "c"


def test_body_sees_every_element_in_order():
    stage, loop = make_loop_stage([5, 6, 7])
    body = loop["loop_body"].get_next_node()
    seen = []
    body.execute = lambda: seen.append(
        (loop["index"].pull_value(), loop["element"].pull_value())
    )

    stage.crawler.start()

    assert seen == [(0, 5), (1, 6), (2, 7)]


def record_iterations(stage, loop):
    """Record (index, element) for every run of the loop body."""
    seen = []
    loop["loop_body"].get_next_node().execute = lambda: seen.append(
        (loop["index"].pull_value(), loop["element"].pull_value())
    )
    stage.crawler.start()
    return seen


def test_reverse_is_off_by_default():
    stage, loop = make_loop_stage([1, 2, 3])

    assert not loop["reverse"].pull_value()
    assert record_iterations(stage, loop) == [(0, 1), (1, 2), (2, 3)]


def test_reverse_iterates_elements_backwards_with_counting_index():
    stage, loop = make_loop_stage([1, 2, 3])
    loop["reverse"].push_value(True)

    assert record_iterations(stage, loop) == [(0, 3), (1, 2), (2, 1)]
    assert loop["element"].pull_value() == 1


@pytest.mark.parametrize(
    "iterable, expected",
    [((1, 2, 3), [3, 2, 1]), ("abc", ["c", "b", "a"]), (range(3), [2, 1, 0])],
)
def test_reverse_works_for_other_sequences(iterable, expected):
    stage, loop = make_loop_stage(iterable)
    loop["reverse"].push_value(True)

    assert [element for _, element in record_iterations(stage, loop)] == expected


def test_reverse_with_empty_iterable_still_completes():
    stage, loop = make_loop_stage([])
    loop["reverse"].push_value(True)

    stage.crawler.start()

    assert "body" not in executed_names(stage)
    assert executed_names(stage)[-2:] == ["loop", "done"]


def test_empty_iterable_skips_body_but_runs_completed():
    stage, _ = make_loop_stage([])

    stage.crawler.start()

    names = executed_names(stage)
    assert "body" not in names
    assert names[-2:] == ["loop", "done"]


def test_loop_without_body_still_completes():
    stage, _ = make_loop_stage([1, 2], with_body=False)

    stage.crawler.start()

    assert executed_names(stage)[-2:] == ["loop", "done"]


@pytest.mark.parametrize(
    "iterable, expected_runs",
    [((1, 2), 2), ({"a": 1, "b": 2, "c": 3}, 3), ("abcd", 4), (range(5), 5)],
)
def test_any_iterable_is_supported(iterable, expected_runs):
    stage, _ = make_loop_stage(iterable)

    stage.crawler.start()

    assert executed_names(stage).count("body") == expected_runs


def test_non_iterable_raises():
    stage, _ = make_loop_stage(5)

    with pytest.raises(TypeError):
        stage.crawler.start()
