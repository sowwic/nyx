import json

import pytest
from PySide6 import QtCore

from nyx.api.v1 import CoreNodes, Stage
from stage_helpers import create_node


@pytest.fixture
def stage():
    return Stage()


def test_metadata_starts_empty_and_keeps_what_is_put_in(stage):
    node = create_node(stage, name="a")
    assert node.metadata == {}

    node.metadata["note"] = "kept"

    assert node.metadata == {"note": "kept"}
    assert node.metadata is node.metadata  # the same dict, so it can be changed


def test_metadata_is_per_object(stage):
    first = create_node(stage, name="a")
    second = create_node(stage, name="b")

    first.metadata["x"] = 1

    assert second.metadata == {}


def test_changing_metadata_is_not_an_edit(stage):
    node = create_node(stage, name="a")
    undo_count = stage.undo_stack.count()
    stage.undo_stack.setClean()

    node.set_graph_view(QtCore.QPointF(1, 2), 3.0)

    assert stage.undo_stack.count() == undo_count
    assert stage.undo_stack.isClean()


def test_serializing_writes_a_copy_of_the_metadata(stage):
    node = create_node(stage, name="a")
    node.metadata["nested"] = {"values": [1, 2]}

    data = node.serialize()
    data["metadata"]["nested"]["values"].append(3)
    data["metadata"]["added"] = True

    assert node.metadata == {"nested": {"values": [1, 2]}}


def test_a_link_does_not_leak_what_it_adds_when_serialized(stage):
    from nyx.api.v1 import Link

    a = create_node(stage, CoreNodes.ACTION, name="a")
    b = create_node(stage, CoreNodes.ACTION, name="b")
    link = Link(stage=stage, source=a["flow"].uuid, target=b["flow"].uuid)
    stage.register_link(link)

    serialized = link.serialize()

    assert "relative_path" in serialized["metadata"]
    assert link.metadata == {}


def test_the_graph_view_of_a_node_is_unknown_until_it_is_set(stage):
    assert create_node(stage, name="a").get_graph_view() is None


def test_the_graph_view_is_stored_in_the_metadata(stage):
    node = create_node(stage, name="a")

    node.set_graph_view(QtCore.QPointF(12.5, -40.0), 2.5)

    assert node.get_graph_view() == (QtCore.QPointF(12.5, -40.0), 2.5)
    assert node.metadata == {
        "graph_view_position": [12.5, -40.0],
        "graph_view_zoom": 2.5,
    }


@pytest.mark.parametrize(
    "metadata",
    [
        {"graph_view_position": [1.0, 2.0]},  # no zoom
        {"graph_view_zoom": 2.0},  # no position
        {"graph_view_position": [1.0], "graph_view_zoom": 2.0},
        {"graph_view_position": "xy", "graph_view_zoom": 2.0},
        {"graph_view_position": [1.0, 2.0], "graph_view_zoom": "big"},
        {"graph_view_position": None, "graph_view_zoom": 2.0},
    ],
)
def test_a_graph_view_that_cannot_be_read_is_unknown(stage, metadata):
    node = create_node(stage, name="a")
    node.metadata.update(metadata)

    assert node.get_graph_view() is None


def test_the_metadata_survives_serialization_and_json(stage):
    node = create_node(stage, name="a")
    node.set_graph_view(QtCore.QPointF(3, 4), 1.5)
    node.metadata["custom"] = {"a": [1, 2]}

    data = json.loads(json.dumps(node.serialize()))
    other = Stage()
    restored = type(node).deserialize(serialized_node=data, parent_node=other.root_node)

    assert restored.metadata == node.metadata
    assert restored.get_graph_view() == (QtCore.QPointF(3, 4), 1.5)


def test_the_graph_view_of_every_node_of_a_saved_stage_comes_back(stage, tmp_path):
    parent = create_node(stage, name="parent")
    child = create_node(stage, name="child", parent=parent)
    stage.root_node.set_graph_view(QtCore.QPointF(1, 2), 1.0)
    parent.set_graph_view(QtCore.QPointF(30, 40), 2.0)
    child.set_graph_view(QtCore.QPointF(-5, 6), 0.5)
    path = tmp_path / "stage.nyx"

    stage.export_json(path)
    loaded = Stage()
    loaded.import_json(path)

    assert loaded.root_node.get_graph_view() == (QtCore.QPointF(1, 2), 1.0)
    loaded_parent = loaded.get_object(parent.path)
    assert loaded_parent.get_graph_view() == (QtCore.QPointF(30, 40), 2.0)
    assert loaded.get_object(child.path).get_graph_view() == (QtCore.QPointF(-5, 6), 0.5)
    assert json.loads(path.read_text())["metadata"]["graph_view_zoom"] == 1.0


def test_older_data_without_metadata_keeps_what_the_node_has(stage):
    node = create_node(stage, name="a")
    node.set_graph_view(QtCore.QPointF(7, 8), 2.0)
    data = node.serialize()
    del data["metadata"]

    type(node).deserialize(serialized_node=data, node=node)

    assert node.get_graph_view() == (QtCore.QPointF(7, 8), 2.0)


def test_loading_replaces_the_metadata_of_an_existing_node(stage):
    node = create_node(stage, name="a")
    node.metadata["stale"] = True
    data = node.serialize()
    data["metadata"] = {"fresh": 1}

    type(node).deserialize(serialized_node=data, node=node)

    assert node.metadata == {"fresh": 1}
