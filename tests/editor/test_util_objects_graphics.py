import pytest
from PySide6 import QtCore, QtWidgets

from nyx.api.v1 import (
    CoreGraphicsObjects,
    CoreNodes,
    CoreUtilObjects,
    NYX_REGISTRY,
    commands,
)
from nyx.editor.graphics.graphics_link import GraphicsLink
from nyx.editor.graphics.graphics_node import GraphicsNode
from nyx.editor.graphics.graphics_plug import GraphicsPlug
from nyx.editor.utils import context_menus
from nyx.stdlib.graphics_objects.group import GraphicsGroup
from nyx.stdlib.graphics_objects.note import GraphicsNote
from nyx.static.vars import DEFAULT_GROUP_COLOR, DEFAULT_NOTE_COLOR


class FancyGraphicsNote(GraphicsNote):
    @classmethod
    def get_type_id(cls) -> str:
        return "test.fancy_note"


@pytest.fixture
def fancy_note_registered():
    NYX_REGISTRY.graphics_objects["test.fancy_note"] = FancyGraphicsNote
    yield FancyGraphicsNote
    NYX_REGISTRY.graphics_objects.pop("test.fancy_note", None)


@pytest.fixture
def create_util_object(stage_editor):
    def _create(type_id=CoreUtilObjects.NOTE, position=(0, 0), node=None, **kwargs):
        command = commands.CreateUtilObjectCommand(
            stage_editor.stage, type_id, node=node, position=position, **kwargs
        )
        stage_editor.stage.push_command(command)
        return command.result_object

    return _create


def select_nodes(stage_editor, *nodes):
    stage_editor.selection_model.clearSelection()
    for node in nodes:
        stage_editor.selection_model.select(
            node.index(), QtCore.QItemSelectionModel.SelectionFlag.Select
        )


def test_builtin_graphics_objects_are_registered(stage_editor):
    expected = {
        CoreGraphicsObjects.NODE: GraphicsNode,
        CoreGraphicsObjects.PLUG: GraphicsPlug,
        CoreGraphicsObjects.LINK: GraphicsLink,
        CoreGraphicsObjects.NOTE: GraphicsNote,
        CoreGraphicsObjects.GROUP: GraphicsGroup,
    }
    for type_id, graphics_cls in expected.items():
        assert NYX_REGISTRY.get_graphics_object_cls(type_id) is graphics_cls


def test_the_editor_application_registers_the_builtin_graphics_objects(
    qapp, monkeypatch
):
    from collections import OrderedDict

    from nyx.application import NyxApplication

    monkeypatch.setattr(NYX_REGISTRY, "_builtin_graphics_objects", OrderedDict())
    monkeypatch.setattr(NYX_REGISTRY, "graphics_objects", OrderedDict())

    NyxApplication.register_builtin_content(qapp)
    assert NYX_REGISTRY.graphics_objects == {}

    qapp.register_builtin_content()
    assert NYX_REGISTRY.get_graphics_object_cls(CoreGraphicsObjects.NODE) is GraphicsNode
    assert NYX_REGISTRY.get_graphics_object_cls(CoreGraphicsObjects.PLUG) is GraphicsPlug
    assert NYX_REGISTRY.get_graphics_object_cls(CoreGraphicsObjects.LINK) is GraphicsLink


def test_registry_reset_keeps_only_the_builtin_graphics_objects(stage_editor):
    NYX_REGISTRY.reset_graphics_objects()
    try:
        assert (
            NYX_REGISTRY.get_graphics_object_cls(CoreGraphicsObjects.NODE)
            is GraphicsNode
        )
        assert NYX_REGISTRY.get_graphics_object_cls(CoreGraphicsObjects.NOTE) is None
    finally:
        NYX_REGISTRY.register_plugin_content()

    assert NYX_REGISTRY.get_graphics_object_cls(CoreGraphicsObjects.NOTE) is GraphicsNote


def test_note_and_group_graphics_come_from_the_stdlib_plugin(stage_editor):
    for cls in (GraphicsNote, GraphicsGroup):
        assert cls.__module__.startswith("nyx.stdlib.")
    contents = NYX_REGISTRY.get_plugin("NyxStdlib").plugin_instance.contents
    assert contents.graphics_objects == [GraphicsNote, GraphicsGroup]


def test_util_objects_are_drawn_with_their_graphics_object(
    stage_editor, create_util_object
):
    note = create_util_object(CoreUtilObjects.NOTE)
    group = create_util_object(CoreUtilObjects.GROUP)

    gr_stage = stage_editor.gr_stage

    assert type(gr_stage.get_gr_util_object(note)) is GraphicsNote
    assert type(gr_stage.get_gr_util_object(group)) is GraphicsGroup


def test_a_util_object_type_can_be_drawn_with_another_graphics_object(
    stage_editor, create_util_object, fancy_note_registered, monkeypatch
):
    from nyx.stdlib.util_objects.note import NoteObject

    note = create_util_object()
    monkeypatch.setattr(
        NoteObject, "get_graphics_object_id", classmethod(lambda cls: "test.fancy_note")
    )
    gr_stage = stage_editor.gr_stage
    gr_stage.remove_util_object(note)

    assert type(gr_stage.add_util_object(note)) is fancy_note_registered


def test_an_unregistered_graphics_object_id_is_not_drawn(
    stage_editor, create_util_object, monkeypatch, caplog
):
    from nyx.stdlib.util_objects.note import NoteObject

    note = create_util_object()
    monkeypatch.setattr(
        NoteObject, "get_graphics_object_id", classmethod(lambda cls: "test.missing")
    )
    gr_stage = stage_editor.gr_stage
    gr_stage.remove_util_object(note)

    with caplog.at_level("ERROR"):
        assert gr_stage.add_util_object(note) is None

    assert "test.missing" in caplog.text


def test_undo_and_redo_update_the_scene(stage_editor, create_util_object):
    note = create_util_object()
    gr_stage = stage_editor.gr_stage
    assert gr_stage.get_gr_util_object(note) is not None

    stage_editor.stage.undo_stack.undo()
    assert gr_stage.gr_util_objects() == []

    stage_editor.stage.undo_stack.redo()
    assert gr_stage.get_gr_util_object(note.uuid) is not None


def test_only_the_util_objects_of_the_scope_are_drawn(
    stage_editor, create_node, create_util_object
):
    inner = create_node(stage_editor.stage, "inner")
    root_note = create_util_object()
    inner_note = create_util_object(node=inner)
    gr_stage = stage_editor.gr_stage
    assert gr_stage.get_gr_util_object(root_note) is not None
    assert gr_stage.get_gr_util_object(inner_note) is None

    stage_editor.set_scope_path(inner)

    assert gr_stage.get_gr_util_object(root_note) is None
    assert gr_stage.get_gr_util_object(inner_note) is not None


def test_item_follows_the_properties_of_the_util_object(
    stage_editor, create_util_object
):
    note = create_util_object(position=(10, 20), size=(300, 200))
    gr_note = stage_editor.gr_stage.get_gr_util_object(note)

    assert gr_note.pos() == QtCore.QPointF(10, 20)
    assert gr_note.item_size == QtCore.QSizeF(300, 200)

    stage_editor.stage.push_command(
        commands.SetUtilObjectPropertiesCommand(
            stage_editor.stage, {note: {"position": [50, 60], "color": "#112233"}}
        )
    )
    assert gr_note.pos() == QtCore.QPointF(50, 60)
    assert gr_note.color.name() == "#112233"


def test_create_note_action_creates_and_selects_the_note(stage_editor):
    view = stage_editor.gr_view
    view.last_scene_mouse_pos = QtCore.QPointF(30, 40)

    view.edit_actions.create_note()

    (gr_note,) = stage_editor.gr_stage.gr_util_objects()
    assert type(gr_note) is GraphicsNote
    assert gr_note.pos() == QtCore.QPointF(30, 40)
    assert gr_note.isSelected()


def test_create_group_wraps_the_selected_nodes(stage_editor, create_node):
    a = create_node(stage_editor.stage, "a")
    b = create_node(stage_editor.stage, "b")
    a.set_position(QtCore.QPointF(0, 0))
    b.set_position(QtCore.QPointF(400, 200))
    stage_editor.gr_stage.rebuild_current_scope()
    select_nodes(stage_editor, a, b)

    stage_editor.gr_view.edit_actions.create_group()

    (gr_group,) = stage_editor.gr_stage.gr_util_objects()
    frame = QtCore.QRectF(gr_group.pos(), gr_group.item_size)
    for node in (a, b):
        gr_node = stage_editor.gr_stage.get_gr_node(node)
        assert frame.contains(
            QtCore.QRectF(gr_node.pos(), QtCore.QSizeF(gr_node.width, gr_node.height))
        )


def test_selecting_a_note_is_not_undone_by_the_node_selection_sync(
    stage_editor, create_node, create_util_object
):
    node = create_node(stage_editor.stage, "n")
    note = create_util_object()
    gr_stage = stage_editor.gr_stage
    gr_note = gr_stage.get_gr_util_object(note)

    gr_note.setSelected(True)

    assert gr_note.isSelected()
    assert gr_stage.selected_gr_util_objects() == [gr_note]
    assert not gr_stage.is_selection_empty()

    select_nodes(stage_editor, node)
    assert gr_stage.get_gr_node(node).isSelected()


def test_selection_survives_a_rebuild(stage_editor, create_util_object):
    note = create_util_object()
    gr_stage = stage_editor.gr_stage
    gr_stage.get_gr_util_object(note).setSelected(True)

    gr_stage.rebuild_current_scope()

    assert gr_stage.get_gr_util_object(note).isSelected()


def test_delete_selected_removes_nodes_and_util_objects_in_one_step(
    stage_editor, create_node, create_util_object
):
    node = create_node(stage_editor.stage, "n")
    note = create_util_object()
    gr_stage = stage_editor.gr_stage
    select_nodes(stage_editor, node)
    gr_stage.get_gr_util_object(note).setSelected(True)

    stage_editor.gr_view.edit_actions.delete_selected()

    assert stage_editor.stage.list_children(stage_editor.stage.root_node) == []
    assert gr_stage.gr_util_objects() == []

    stage_editor.stage.undo_stack.undo()
    assert [
        n.name for n in stage_editor.stage.list_children(stage_editor.stage.root_node)
    ] == ["n"]
    assert gr_stage.get_gr_util_object(note.uuid) is not None


def test_moving_items_pushes_one_command(stage_editor, create_node, create_util_object):
    node = create_node(stage_editor.stage, "n")
    note = create_util_object(position=(0, 0))
    gr_stage = stage_editor.gr_stage
    undo_stack = stage_editor.stage.undo_stack
    count = undo_stack.count()

    gr_stage.get_gr_node(node).setPos(100, 100)
    gr_stage.get_gr_util_object(note).setPos(50, 60)
    gr_stage.commit_moves()

    assert node.position() == QtCore.QPointF(100, 100)
    assert note.position == QtCore.QPointF(50, 60)
    assert undo_stack.count() == count + 1  # one macro

    undo_stack.undo()
    assert node.position() == QtCore.QPointF(0, 0)
    assert note.position == QtCore.QPointF(0, 0)


def test_commit_moves_without_a_move_pushes_nothing(stage_editor, create_util_object):
    create_util_object()
    count = stage_editor.stage.undo_stack.count()

    stage_editor.gr_stage.commit_moves()

    assert stage_editor.stage.undo_stack.count() == count


def test_resizing_pushes_a_command(stage_editor, create_util_object):
    note = create_util_object(size=(200, 100))
    gr_note = stage_editor.gr_stage.get_gr_util_object(note)

    gr_note._resizing = True
    gr_note._size = QtCore.QSizeF(320, 240)
    gr_note.mouseReleaseEvent(QtWidgets.QGraphicsSceneMouseEvent())

    assert note.size == QtCore.QSizeF(320, 240)
    stage_editor.stage.undo_stack.undo()
    assert note.size == QtCore.QSizeF(200, 100)


def test_moving_a_group_moves_the_nodes_inside(
    stage_editor, create_node, create_util_object
):
    inside = create_node(stage_editor.stage, "inside")
    outside = create_node(stage_editor.stage, "outside")
    inside.set_position(QtCore.QPointF(20, 40))
    outside.set_position(QtCore.QPointF(2000, 2000))
    group = create_util_object(CoreUtilObjects.GROUP, position=(0, 0), size=(600, 400))
    gr_stage = stage_editor.gr_stage
    gr_stage.rebuild_current_scope()
    gr_group = gr_stage.get_gr_util_object(group)

    gr_group._enclosed = gr_group.enclosed_items()
    gr_group.setPos(100, 50)
    gr_stage.commit_moves()

    assert group.position == QtCore.QPointF(100, 50)
    assert inside.position() == QtCore.QPointF(120, 90)
    assert outside.position() == QtCore.QPointF(2000, 2000)


def test_util_object_context_menu(qtbot, stage_editor, create_util_object):
    gr_note = stage_editor.gr_stage.get_gr_util_object(create_util_object())
    parent = QtWidgets.QWidget()
    qtbot.addWidget(parent)

    menu = context_menus.build_util_object_context_menu(parent, gr_note)

    labels = [action.text() for action in menu.actions() if not action.isSeparator()]
    assert labels[:2] == ["Edit...", "Color"]
    assert "Delete" in labels


def test_set_color_pushes_a_command(stage_editor, create_util_object):
    note = create_util_object()
    gr_note = stage_editor.gr_stage.get_gr_util_object(note)

    gr_note.set_color("#102030")

    assert note.color == "#102030"
    stage_editor.stage.undo_stack.undo()
    assert note.color == DEFAULT_NOTE_COLOR


def test_notes_and_groups_paint(stage_editor, create_util_object):
    from PySide6 import QtGui

    create_util_object(CoreUtilObjects.GROUP, position=(0, 0), size=(300, 200))
    note = create_util_object(
        position=(20, 40), size=(120, 80), properties={"text": "hello\nworld"}
    )
    stage_editor.gr_stage.get_gr_util_object(note).setSelected(True)

    image = QtGui.QImage(400, 300, QtGui.QImage.Format_ARGB32)
    image.fill(QtGui.QColor("black"))
    painter = QtGui.QPainter(image)
    area = QtCore.QRectF(0, 0, 400, 300)
    stage_editor.gr_stage.render(painter, area, area)
    painter.end()

    # The note is drawn in its color inside the selection outline.
    assert image.pixelColor(60, 80) == QtGui.QColor(note.color)


def test_moving_a_group_moves_the_notes_and_groups_inside(
    stage_editor, create_util_object
):
    group = create_util_object(CoreUtilObjects.GROUP, position=(0, 0), size=(600, 400))
    inner_note = create_util_object(position=(20, 40), size=(100, 60))
    inner_group = create_util_object(
        CoreUtilObjects.GROUP, position=(200, 100), size=(150, 100)
    )
    straddling = create_util_object(position=(550, 350), size=(200, 100))
    far_away = create_util_object(position=(2000, 2000))
    gr_stage = stage_editor.gr_stage
    gr_group = gr_stage.get_gr_util_object(group)

    gr_group._enclosed = gr_group.enclosed_items()
    gr_group.setPos(100, 50)
    gr_stage.commit_moves()

    assert group.position == QtCore.QPointF(100, 50)
    assert inner_note.position == QtCore.QPointF(120, 90)
    assert inner_group.position == QtCore.QPointF(300, 150)
    assert straddling.position == QtCore.QPointF(550, 350)
    assert far_away.position == QtCore.QPointF(2000, 2000)

    stage_editor.stage.undo_stack.undo()
    assert group.position == QtCore.QPointF(0, 0)
    assert inner_note.position == QtCore.QPointF(20, 40)
    assert inner_group.position == QtCore.QPointF(200, 100)


def test_selected_notes_inside_a_group_are_not_moved_twice(
    stage_editor, create_util_object
):
    group = create_util_object(CoreUtilObjects.GROUP, position=(0, 0), size=(600, 400))
    note = create_util_object(position=(20, 40), size=(100, 60))
    gr_stage = stage_editor.gr_stage
    gr_stage.get_gr_util_object(note).setSelected(True)

    gr_group = gr_stage.get_gr_util_object(group)

    assert gr_group.enclosed_items() == []


def test_pressing_a_group_carries_a_node_that_was_selected(
    stage_editor, create_node, create_util_object
):
    node = create_node(stage_editor.stage, "n")
    node.set_position(QtCore.QPointF(20, 40))
    group = create_util_object(CoreUtilObjects.GROUP, position=(0, 0), size=(600, 400))
    gr_stage = stage_editor.gr_stage
    gr_stage.rebuild_current_scope()
    gr_node = gr_stage.get_gr_node(node)
    gr_group = gr_stage.get_gr_util_object(group)
    gr_node.setSelected(True)

    press = QtWidgets.QGraphicsSceneMouseEvent(QtCore.QEvent.GraphicsSceneMousePress)
    press.setButton(QtCore.Qt.LeftButton)
    press.setPos(QtCore.QPointF(300, 300))
    press.setScenePos(QtCore.QPointF(300, 300))
    gr_group.mousePressEvent(press)

    assert gr_group.isSelected()
    assert not gr_node.isSelected()
    assert gr_group._enclosed == [gr_node]

    gr_group.setPos(100, 50)
    gr_stage.commit_moves()
    assert node.position() == QtCore.QPointF(120, 90)


@pytest.fixture
def graphics_stage_config(main_window, restore_config):
    return restore_config(
        main_window.config.values.editor_widgets.graphics_stage,
        "default_note_color",
        "default_group_color",
    )


def test_new_notes_and_groups_get_the_configured_colors(
    stage_editor, graphics_stage_config
):
    graphics_stage_config.default_note_color = "#102030"
    graphics_stage_config.default_group_color = "#405060"
    actions = stage_editor.gr_view.edit_actions

    actions.create_note()
    actions.create_group()

    colors = {
        type(gr_util.util_object).__name__: gr_util.util_object.color
        for gr_util in stage_editor.gr_stage.gr_util_objects()
    }
    assert colors == {"NoteObject": "#102030", "GroupObject": "#405060"}


def test_an_invalid_configured_color_falls_back_to_the_default(
    stage_editor, graphics_stage_config, caplog
):
    graphics_stage_config.default_note_color = "not a color"

    with caplog.at_level("WARNING"):
        stage_editor.gr_view.edit_actions.create_note()

    (gr_note,) = stage_editor.gr_stage.gr_util_objects()
    assert gr_note.util_object.color == DEFAULT_NOTE_COLOR
    assert "default_note_color" in caplog.text


def test_config_defaults_are_the_default_colors(graphics_stage_config):
    defaults = type(graphics_stage_config)()

    assert defaults.default_note_color == DEFAULT_NOTE_COLOR
    assert defaults.default_group_color == DEFAULT_GROUP_COLOR


def test_nodes_without_a_graphics_object_id_are_not_drawn(
    stage_editor, create_node, monkeypatch
):
    from nyx.api.v1 import Node

    node = create_node(stage_editor.stage, type_id=CoreNodes.ACTION)
    monkeypatch.setattr(Node, "get_graphics_object_id", classmethod(lambda cls: None))
    gr_stage = stage_editor.gr_stage
    gr_stage.remove_node(node)

    assert gr_stage.add_node(node) is None
    assert gr_stage.get_gr_node(node) is None

    gr_stage.rebuild_current_scope()
    assert gr_stage.gr_nodes() == []


def test_util_objects_without_a_graphics_object_id_are_not_drawn(
    stage_editor, create_util_object, monkeypatch
):
    from nyx.stdlib.util_objects.note import NoteObject

    note = create_util_object()
    monkeypatch.setattr(
        NoteObject, "get_graphics_object_id", classmethod(lambda cls: None)
    )
    gr_stage = stage_editor.gr_stage
    gr_stage.remove_util_object(note)

    assert gr_stage.add_util_object(note) is None
    gr_stage.rebuild_current_scope()
    assert gr_stage.gr_util_objects() == []


def test_components_without_a_graphics_object_id_get_no_plug(
    stage_editor, create_node, monkeypatch
):
    from nyx.api.v1 import NodeComponent

    node = create_node(stage_editor.stage, type_id=CoreNodes.ACTION)
    gr_node = stage_editor.gr_stage.get_gr_node(node)
    assert gr_node.plugs

    monkeypatch.setattr(
        NodeComponent, "get_graphics_object_id", classmethod(lambda cls: None)
    )
    gr_node.refresh()

    assert gr_node.plugs == []


def test_a_node_whose_type_sets_a_graphics_object_id_is_drawn_with_it(
    stage_editor, create_node, monkeypatch
):
    from nyx.api.v1 import Node

    class CustomGraphicsNode(GraphicsNode):
        @classmethod
        def get_type_id(cls) -> str:
            return "test.type_node"

    NYX_REGISTRY.graphics_objects["test.type_node"] = CustomGraphicsNode
    try:
        node = create_node(stage_editor.stage, type_id=CoreNodes.ACTION)
        monkeypatch.setattr(
            Node, "get_graphics_object_id", classmethod(lambda cls: "test.type_node")
        )
        gr_stage = stage_editor.gr_stage
        gr_stage.remove_node(node)

        assert type(gr_stage.add_node(node)) is CustomGraphicsNode
    finally:
        NYX_REGISTRY.graphics_objects.pop("test.type_node", None)
