from nyx.api.v1 import CoreDatatypes, CoreNodes, Stage
from nyx.core.datatypes.datatype import value_to_rows
from nyx.core.models.components_model import NodeComponentsModel
from nyx.core.node_component import NodeComponent
from stage_helpers import create_node

ROWS = NodeComponent.Roles.VALUE_ROWS
LIMITS = {
    "max_rows": NodeComponentsModel.MAX_VALUE_ROWS,
    "max_length": NodeComponentsModel.MAX_VALUE_ROW_LENGTH,
}


def test_dict_rows_have_the_key_and_the_value_as_text():
    assert value_to_rows({"a": 1, "b": [1, 2]}, **LIMITS) == [
        {"key": "a", "value": "1", "more": False},
        {"key": "b", "value": "[1, 2]", "more": False},
    ]


def test_list_tuple_and_set_rows_have_the_position_as_key():
    assert [row["key"] for row in value_to_rows(["x", "y"], **LIMITS)] == ["0", "1"]
    assert [row["value"] for row in value_to_rows(("x", "y"), **LIMITS)] == ["x", "y"]
    assert len(value_to_rows({1, 2, 3}, **LIMITS)) == 3


def test_other_values_and_empty_collections_have_no_rows():
    assert value_to_rows("text", **LIMITS) == []
    assert value_to_rows(5, **LIMITS) == []
    assert value_to_rows(None, **LIMITS) == []
    assert value_to_rows({}, **LIMITS) == []
    assert value_to_rows([], **LIMITS) == []


def test_rows_are_cut_off_with_a_note_of_the_rest():
    rows = value_to_rows(list(range(10)), max_rows=3, max_length=500)

    assert [row["value"] for row in rows[:3]] == ["0", "1", "2"]
    assert rows[3] == {"key": "…", "value": "7 more", "more": True}
    assert len(rows) == 4


def test_long_values_are_cut_with_an_ellipsis():
    (row,) = value_to_rows({"k": "x" * 50}, max_rows=10, max_length=10)

    assert row["value"] == "x" * 9 + "…"


def test_dict_node_result_has_rows_in_the_model():
    stage = Stage()
    node = create_node(stage, CoreNodes.DICT)
    result = node["result"]
    assert result.datatype.type_id == CoreDatatypes.DICT

    rows = node.components_model.data(result.index(), ROWS)
    assert rows == []  # no values collected yet


def test_value_component_with_a_scalar_has_no_rows():
    stage = Stage()
    node = create_node(stage, CoreNodes.VALUE)

    assert node.components_model.data(node["value"].index(), ROWS) == []


def test_changing_the_value_reports_new_rows_to_the_views():
    stage = Stage()
    node = create_node(stage, CoreNodes.VALUE)
    component = node["value"]
    changed = []
    node.components_model.dataChanged.connect(
        lambda top_left, bottom_right, roles: changed.append(list(roles))
    )

    component.push_value({"a": 1})

    assert [int(ROWS)] in changed
    assert node.components_model.data(component.index(), ROWS) == [
        {"key": "a", "value": "1", "more": False}
    ]


def test_model_gives_the_views_rows_up_to_its_limits(monkeypatch):
    monkeypatch.setattr(NodeComponentsModel, "MAX_VALUE_ROWS", 2)
    monkeypatch.setattr(NodeComponentsModel, "MAX_VALUE_ROW_LENGTH", 4)
    stage = Stage()
    node = create_node(stage, CoreNodes.VALUE)
    node["value"].push_value(["abcdefgh", "b", "c"])

    rows = node.components_model.data(node["value"].index(), ROWS)

    assert [row["value"] for row in rows] == ["abc…", "b", "1 more"]
