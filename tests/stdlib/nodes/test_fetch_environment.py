import os

from nyx.api.v1 import CoreDatatypes, CoreNodeComponents, CoreNodes, Stage
from nyx.core.node_component import NodeComponent
from stage_helpers import create_node


def test_fetch_environment_creation():
    stage = Stage()
    node = create_node(stage, CoreNodes.FETCH_ENVIRONMENT)

    assert node.components_model.rowCount() == 3
    flow_in = node["flow"]
    assert flow_in.get_type_id() == CoreNodeComponents.FLOW
    assert (flow_in.writable, flow_in.readable) == (True, False)
    flow_out = node["next"]
    assert flow_out.get_type_id() == CoreNodeComponents.FLOW
    assert (flow_out.writable, flow_out.readable) == (False, True)

    value = node["environment"]
    assert value.get_type_id() == CoreNodeComponents.VALUE
    assert value.readable is True
    assert value.writable is False
    assert value.datatype.type_id == CoreDatatypes.DICT


def test_fetch_environment_stores_the_environment_when_executed(monkeypatch):
    stage = Stage()
    node = create_node(stage, CoreNodes.FETCH_ENVIRONMENT)
    monkeypatch.setenv("NYX_TEST_FETCH_ENV", "first")
    assert node["environment"].pull_value() in ({}, None, "")  # not fetched yet

    node.execute()

    assert node["environment"].pull_value() == dict(os.environ)
    assert node["environment"].pull_value()["NYX_TEST_FETCH_ENV"] == "first"


def test_fetched_environment_is_a_snapshot(monkeypatch):
    stage = Stage()
    node = create_node(stage, CoreNodes.FETCH_ENVIRONMENT)
    monkeypatch.setenv("NYX_TEST_FETCH_ENV", "first")
    node.execute()

    monkeypatch.setenv("NYX_TEST_FETCH_ENV", "second")
    assert node["environment"].pull_value()["NYX_TEST_FETCH_ENV"] == "first"

    node.execute()
    assert node["environment"].pull_value()["NYX_TEST_FETCH_ENV"] == "second"


def test_changing_the_fetched_dict_does_not_change_the_environment():
    stage = Stage()
    node = create_node(stage, CoreNodes.FETCH_ENVIRONMENT)
    node.execute()
    node["environment"].pull_value()["NYX_TEST_NOT_SET"] = "x"

    assert "NYX_TEST_NOT_SET" not in os.environ


def test_fetch_environment_rows_follow_the_fetched_value(monkeypatch):
    stage = Stage()
    node = create_node(stage, CoreNodes.FETCH_ENVIRONMENT)
    monkeypatch.setenv("NYX_TEST_FETCH_ENV", "visible")
    index = node["environment"].index()
    rows = NodeComponent.Roles.VALUE_ROWS

    assert node.components_model.data(index, rows) == []
    node.execute()

    assert {"key": "NYX_TEST_FETCH_ENV", "value": "visible", "more": False} in (
        node.components_model.data(index, rows)
    )
