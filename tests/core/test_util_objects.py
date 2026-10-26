from PySide6 import QtCore

from nyx.api.v1 import (
    CoreGraphicsObjects,
    CoreNodes,
    CoreUtilObjects,
    NYX_REGISTRY,
    Node,
    Stage,
    UtilObject,
    commands,
)


def _create_node(stage: Stage, name="node", parent=None) -> Node:
    command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.EMPTY, name=name, parent_node=parent
    )
    stage.push_command(command)
    return command.result_node


def _create_util(stage: Stage, type_id=CoreUtilObjects.NOTE, node=None, **kwargs):
    command = commands.CreateUtilObjectCommand(
        stage=stage, type_id=type_id, node=node, **kwargs
    )
    stage.push_command(command)
    return command.result_object


def test_core_util_objects_are_registered():
    assert NYX_REGISTRY.util_objects.keys() >= {
        CoreUtilObjects.NOTE,
        CoreUtilObjects.GROUP,
    }
    note_cls = NYX_REGISTRY.get_util_object_cls(CoreUtilObjects.NOTE)
    assert note_cls.get_source_plugin_name() == "NyxCore"


def test_create_note_registers_it_in_the_stage():
    stage = Stage()
    node = _create_node(stage)

    note = _create_util(
        stage, node=node, position=(10, 20), properties={"text": "hello"}
    )

    assert node.util_objects == [note]
    assert stage.get_object(note.uuid) is note
    assert note.node is node
    assert note.position == QtCore.QPointF(10, 20)
    assert note.text == "hello"


def test_create_undo_redo():
    stage = Stage()
    node = _create_node(stage)
    note = _create_util(stage, node=node)
    uuid = note.uuid

    stage.undo_stack.undo()
    assert node.util_objects == []
    assert uuid not in stage.uuid_map

    stage.undo_stack.redo()
    assert [each.uuid for each in node.util_objects] == [uuid]
    assert stage.get_object(uuid) is node.util_objects[0]


def test_util_objects_are_serialized_under_the_node():
    stage = Stage()
    node = _create_node(stage)
    _create_util(stage, node=node, position=(1, 2), properties={"text": "a"})
    _create_util(stage, CoreUtilObjects.GROUP, node=node, properties={"title": "G"})

    data = node.serialize()[Node.UTIL_OBJECTS_KEY]

    assert [each["type_id"] for each in data] == [
        CoreUtilObjects.NOTE,
        CoreUtilObjects.GROUP,
    ]
    assert data[0]["position"] == [1.0, 2.0]
    assert data[0]["text"] == "a"
    assert data[1]["title"] == "G"
    assert Node.UTIL_OBJECTS_KEY not in node.serialize()["children"]


def test_util_objects_round_trip_through_the_stage_file(tmp_path):
    stage = Stage()
    node = _create_node(stage)
    note = _create_util(
        stage,
        node=node,
        position=(5, 6),
        size=(300, 200),
        properties={"text": "keep", "color": "#112233"},
    )
    path = tmp_path / f"stage{stage.FILE_EXTENSION}"
    stage.export_json(path)

    other = Stage()
    other.import_json(path)

    restored_node = other.get_object(node.path)
    (restored,) = restored_node.util_objects
    assert restored.uuid == note.uuid
    assert restored.text == "keep"
    assert restored.color == "#112233"
    assert restored.position == QtCore.QPointF(5, 6)
    assert restored.size == QtCore.QSizeF(300, 200)


def test_graphics_object_id_override_is_serialized_and_restored():
    stage = Stage()
    node = _create_node(stage)
    note = _create_util(stage, node=node)
    assert note.graphics_object_id == CoreGraphicsObjects.NOTE
    assert UtilObject.GRAPHICS_OBJECT_ID_KEY not in note.serialize()

    note.graphics_object_id = "test.fancy_note"
    data = node.serialize()

    assert data[Node.UTIL_OBJECTS_KEY][0]["graphics_object_id"] == "test.fancy_note"
    other = Stage()
    restored = UtilObject.deserialize(
        node=other.root_node, serialized_data=data[Node.UTIL_OBJECTS_KEY][0]
    )
    assert restored.graphics_object_id == "test.fancy_note"


def test_node_and_component_graphics_object_ids():
    stage = Stage()
    node = _create_node(stage)
    assert node.graphics_object_id == CoreGraphicsObjects.NODE

    class Custom(Node):
        GRAPHICS_OBJECT_ID = "test.custom"

    assert Custom.GRAPHICS_OBJECT_ID == "test.custom"
    node.graphics_object_id = "test.custom"
    assert node.serialize()["graphics_object_id"] == "test.custom"
    node.graphics_object_id = None
    assert "graphics_object_id" not in node.serialize()


def test_set_properties_undo_redo():
    stage = Stage()
    note = _create_util(stage)
    old_position = note.position

    stage.push_command(
        commands.SetUtilObjectPropertiesCommand(
            stage, {note: {"position": [40, 50], "text": "x"}}
        )
    )
    assert note.position == QtCore.QPointF(40, 50)
    assert note.text == "x"

    stage.undo_stack.undo()
    assert note.position == old_position
    assert note.text == ""

    stage.undo_stack.redo()
    assert note.text == "x"


def test_size_has_a_minimum():
    stage = Stage()
    note = _create_util(stage)

    note.size = (1, 1)

    assert note.size.width() == UtilObject.MIN_SIZE[0]
    assert note.size.height() == UtilObject.MIN_SIZE[1]


def test_delete_undo_restores_the_object_with_its_uuid():
    stage = Stage()
    node = _create_node(stage)
    note = _create_util(stage, node=node, properties={"text": "back"})
    uuid = note.uuid

    stage.push_command(commands.DeleteUtilObjectCommand(stage, [note]))
    assert node.util_objects == []
    assert uuid not in stage.uuid_map

    stage.undo_stack.undo()
    restored = stage.get_object(uuid)
    assert restored.text == "back"
    assert restored.node is node


def test_deleting_a_node_restores_its_util_objects_on_undo():
    stage = Stage()
    node = _create_node(stage)
    note = _create_util(stage, node=node, properties={"text": "kept"})
    uuid = note.uuid

    stage.push_command(commands.DeleteNodeCommand(stage, [node]))
    assert uuid not in stage.uuid_map

    stage.undo_stack.undo()
    assert stage.get_object(uuid).text == "kept"


def test_pasted_nodes_copy_their_util_objects_with_stable_uuids():
    stage = Stage()
    node = _create_node(stage)
    _create_util(stage, node=node, properties={"text": "copy me"})
    command = commands.PasteNodesCommand(
        stage=stage,
        serialize_nodes=[node.serialize()],
        position=QtCore.QPointF(100, 100),
    )

    stage.push_command(command)
    pasted = [
        each
        for each in stage.root_node.list_children()
        if each is not node and each.util_objects
    ]
    assert len(pasted) == 1
    uuid = pasted[0].util_objects[0].uuid
    assert uuid != node.util_objects[0].uuid

    stage.undo_stack.undo()
    stage.undo_stack.redo()
    again = [each for each in stage.root_node.list_children() if each is not node]
    assert again[0].util_objects[0].uuid == uuid
