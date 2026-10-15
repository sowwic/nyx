import json

from PySide6 import QtWidgets

from nyx.editor.utils import clipboard


def _set_clipboard(text: str) -> None:
    QtWidgets.QApplication.clipboard().setText(text)


def test_serialize_copies_top_level_nodes_only(stage_editor, create_node):
    stage = stage_editor.stage
    parent = create_node(stage, "parent")
    child = create_node(stage, "child", parent=parent)

    clipboard.serialize_nodes_to_clipboard([parent, child])

    data = json.loads(QtWidgets.QApplication.clipboard().text())
    assert [n["name"] for n in data["nyx_nodes"]] == ["parent"]
    assert stage.get_object(parent.path)  # copy does not delete


def test_serialize_with_delete_cuts_nodes(stage_editor, create_node):
    stage = stage_editor.stage
    node = create_node(stage, "doomed")

    clipboard.serialize_nodes_to_clipboard([node], delete=True)

    assert stage.list_children(stage.root_node) == []
    stage.undo_stack.undo()
    assert [n.name for n in stage.list_children(stage.root_node)] == ["doomed"]


def test_get_serialized_nodes_roundtrip(stage_editor, create_node):
    node = create_node(stage_editor.stage, "roundtrip")
    clipboard.serialize_nodes_to_clipboard([node])
    serialized = clipboard.get_serialized_nodes_from_clipboard()
    assert [n["name"] for n in serialized] == ["roundtrip"]


def test_get_serialized_nodes_ignores_non_json(qapp):
    _set_clipboard("definitely not json")
    assert clipboard.get_serialized_nodes_from_clipboard() == []


def test_get_serialized_nodes_ignores_json_without_nodes(qapp):
    _set_clipboard(json.dumps({"something": "else"}))
    assert clipboard.get_serialized_nodes_from_clipboard() == []
