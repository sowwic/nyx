import pathlib

import pytest

from nyx.api.v1 import CoreDatatypes, CoreNodes, Stage, commands


def make_node(stage, type_id, name=None):
    command = commands.CreateNodeCommand(stage=stage, type_id=type_id, name=name)
    stage.push_command(command)
    return command.result_node


def make_cast(object_value, target_type, stage=None):
    """Build flow_start -> type_cast with the inputs set."""
    stage = stage or Stage()
    start = make_node(stage, CoreNodes.FLOW_START, name="start")
    node = make_node(stage, CoreNodes.TYPE_CAST, name="cast")
    start["flow"] >> node["flow"]
    node["type"].push_value(target_type)
    node["object"].push_value(object_value)
    return node


def run(node):
    node.stage.crawler.start()
    return node["result"].pull_value()


def test_type_cast_node_creation():
    node = make_node(Stage(), CoreNodes.TYPE_CAST)

    assert node.get_type_id() == CoreNodes.TYPE_CAST
    assert node["flow"].readable and node["flow"].writable
    assert node["type"].datatype_id == CoreDatatypes.TYPE
    assert node["type"].writable and not node["type"].readable
    assert node["object"].datatype_id == CoreDatatypes.OBJECT
    assert node["object"].writable and not node["object"].readable
    assert node["result"].datatype_id == CoreDatatypes.OBJECT
    assert node["result"].readable and not node["result"].writable
    assert node.get_description()


@pytest.mark.parametrize(
    "object_value, target_type, expected",
    [
        (5, str, "5"),
        (3.9, int, 3),
        (1, bool, True),
        (0, bool, False),
        (2, float, 2.0),
        ([1, 2], tuple, (1, 2)),
        ("a/b", pathlib.PurePosixPath, pathlib.PurePosixPath("a/b")),
        (7, object, 7),
    ],
)
def test_result_is_the_object_converted_to_the_type(object_value, target_type, expected):
    result = run(make_cast(object_value, target_type))

    assert result == expected
    assert type(result) is type(expected)


def test_string_result_is_not_evaluated():
    assert run(make_cast(5, str)) == "5"
    assert run(make_cast(12.5, str)) == "12.5"


def test_object_of_the_type_is_not_converted_again():
    class Thing:
        def __init__(self, other=None):
            raise AssertionError("converted although it already is a Thing")

    value = Thing.__new__(Thing)

    assert run(make_cast(value, Thing)) is value


def test_type_can_be_typed_as_an_expression():
    node = make_cast(7, "float")

    assert run(node) == 7.0


def test_result_is_not_there_before_the_node_runs():
    node = make_cast("5", int)

    assert node["result"].pull_value() != 5


def test_result_can_be_linked_to_other_nodes():
    stage = Stage()
    cast = make_cast(3, str, stage)
    log = make_node(stage, CoreNodes.LOG, name="log")
    cast["flow"] >> log["flow"]
    cast["result"] >> log["message"]

    stage.crawler.start()

    assert log["message"].pull_value() == "3"


def test_object_is_taken_through_links():
    stage = Stage()
    source = make_node(stage, CoreNodes.VALUE, name="source")
    source["value"].push_value("42")
    cast = make_cast(0, int, stage)
    source["value"] >> cast["object"]

    assert run(cast) == 42


def test_invalid_type_fails_the_execution():
    node = make_cast(1, int)
    node["type"].set_datatype(CoreDatatypes.OBJECT)
    node["type"].push_value(3)

    with pytest.raises(TypeError, match="not a type"):
        node.stage.crawler.start()


def test_value_that_cant_be_converted_fails_the_execution():
    node = make_cast("abc", int)

    with pytest.raises(ValueError):
        node.stage.crawler.start()


def test_subtitle_shows_the_type():
    assert make_cast(5, str).subtitle == "str"


def test_class_values_can_be_shown_and_saved():
    import json

    node = make_node(Stage(), CoreNodes.TYPE_CAST)
    node["type"].push_value(float)
    model = node.components_model
    index = node["type"].index()

    # Views get the name of the class, not the class (which QML can't show)
    assert model.data(index, node["type"].Roles.RAW_VALUE) == "float"
    assert model.data(index, node["type"].Roles.CACHED_VALUE) == "float"
    assert node["type"].raw_value is float

    serialized = node.serialize()
    json.dumps(serialized)
    type_data = next(c for c in serialized["components"] if c["name"] == "type")
    assert type_data["value"] == "float"


def test_class_value_is_restored_from_a_saved_file(tmp_path):
    node = make_node(Stage(), CoreNodes.TYPE_CAST, name="cast")
    node["type"].push_value(float)
    file_path = tmp_path / "cast.nyx"
    node.export_to_json(file_path)

    restored = make_node(Stage(), CoreNodes.TYPE_CAST, name="restored")
    restored["type"].push_value(int)
    restored.load_from_json(file_path)

    assert restored["type"].cached_value is float
