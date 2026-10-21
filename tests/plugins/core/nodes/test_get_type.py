import pathlib

import pytest

from nyx.api.v1 import CoreDatatypes, CoreNodes, Stage, commands


def make_node(stage, type_id, name=None):
    command = commands.CreateNodeCommand(stage=stage, type_id=type_id, name=name)
    stage.push_command(command)
    return command.result_node


def make_get_type(object_value, stage=None):
    """Build flow_start -> get_type with the object set."""
    stage = stage or Stage()
    start = make_node(stage, CoreNodes.FLOW_START, name="start")
    node = make_node(stage, CoreNodes.GET_TYPE, name="get_type")
    start["flow"] >> node["flow"]
    node["object"].push_value(object_value)
    return node


def run(node):
    node.stage.crawler.start()
    return node["type"].pull_value()


def test_get_type_node_creation():
    node = make_node(Stage(), CoreNodes.GET_TYPE)

    assert node.get_type_id() == CoreNodes.GET_TYPE
    assert node["flow"].readable and node["flow"].writable
    assert node["object"].datatype_id == CoreDatatypes.OBJECT
    assert node["object"].writable and not node["object"].readable
    assert node["type"].datatype_id == CoreDatatypes.TYPE
    assert node["type"].readable and not node["type"].writable
    assert node.get_description()


@pytest.mark.parametrize(
    "object_value, expected",
    [
        (5, int),
        (1.5, float),
        (True, bool),
        ("text", str),
        (pathlib.PurePosixPath("a"), pathlib.PurePosixPath),
    ],
)
def test_type_is_the_class_of_the_object(object_value, expected):
    assert run(make_get_type(object_value)) is expected


def test_string_value_is_evaluated_before_its_type_is_taken():
    assert run(make_get_type("[1, 2]")) is list  # typed as an expression


def test_type_can_be_linked_to_a_type_cast():
    stage = Stage()
    get_type = make_get_type(2.5, stage)
    cast = make_node(stage, CoreNodes.TYPE_CAST, name="cast")
    get_type["flow"] >> cast["flow"]
    get_type["type"] >> cast["type"]
    cast["object"].push_value(7)

    stage.crawler.start()

    assert cast["result"].pull_value() == 7.0
    assert type(cast["result"].pull_value()) is float


def test_type_is_not_there_before_the_node_runs():
    assert make_get_type(5)["type"].pull_value() is object


def test_object_is_taken_through_links():
    stage = Stage()
    source = make_node(stage, CoreNodes.VALUE, name="source")
    source["value"].push_value(3)
    node = make_get_type(0, stage)
    source["value"] >> node["object"]

    assert run(node) is int


def test_subtitle_shows_the_type():
    node = make_get_type(5)
    run(node)

    assert node.subtitle == "int"
