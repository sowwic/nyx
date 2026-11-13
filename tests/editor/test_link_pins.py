import pytest
from PySide6 import QtCore, QtGui, QtTest

from nyx.api.v1 import CoreNodes, Link, Stage, commands
from nyx.editor.graphics.graphics_link_pin import GraphicsLinkPin
from nyx.editor.graphics.link_path import build_link_path, find_pin_index
from nyx.static.enums import LinkStyle

START = QtCore.QPointF(0.0, 0.0)
END = QtCore.QPointF(400.0, 0.0)
PIN_A = QtCore.QPointF(100.0, 80.0)
PIN_B = QtCore.QPointF(300.0, -80.0)


def path_points(path):
    return [QtCore.QPointF(path.elementAt(i)) for i in range(path.elementCount())]


def current_gr_link(editor, link):
    """The item drawing the link, the scene is rebuilt after every command."""
    return editor.gr_stage.get_gr_link(link)


@pytest.fixture
def flow_link(stage_editor, create_node):
    stage = stage_editor.stage
    a = create_node(stage, "a", type_id=CoreNodes.ACTION)
    b = create_node(stage, "b", type_id=CoreNodes.ACTION)
    stage.push_command(
        commands.LinkNodeComponentsCommand(
            stage=stage, source=a["flow"], target=b["flow"]
        )
    )
    (gr_link,) = stage_editor.gr_stage.gr_links()
    return stage_editor, stage.get_object(gr_link.uuid), gr_link


# ======== Path ========= #


@pytest.mark.parametrize("style", list(LinkStyle))
def test_path_passes_through_every_pin(style):
    path = build_link_path(style, START, END, [PIN_A, PIN_B])
    points = path_points(path)
    assert PIN_A in points
    assert PIN_B in points
    assert points[0] == START
    assert points[-1] == END


@pytest.mark.parametrize("style", list(LinkStyle))
def test_no_pins_gives_the_plain_path(style):
    assert path_points(build_link_path(style, START, END)) == path_points(
        build_link_path(style, START, END, [])
    )


def test_new_pin_goes_into_the_closest_part_of_the_link():
    style = LinkStyle.DIRECT
    assert find_pin_index(style, START, END, [], QtCore.QPointF(200, 5)) == 0
    pins = [PIN_A, PIN_B]
    assert find_pin_index(style, START, END, pins, QtCore.QPointF(40, 30)) == 0
    assert find_pin_index(style, START, END, pins, QtCore.QPointF(200, 0)) == 1
    assert find_pin_index(style, START, END, pins, QtCore.QPointF(360, -30)) == 2


# ======== Core ========= #


def test_pins_are_saved_with_the_link(flow_link):
    _editor, link, _gr_link = flow_link
    assert "pins" not in link.serialize()
    link.pins = [PIN_A, PIN_B]
    data = link.serialize()
    assert data["pins"] == [[100.0, 80.0], [300.0, -80.0]]

    restored = Link.deserialize(link.stage, data)
    assert restored.pins == [PIN_A, PIN_B]


def test_old_links_without_pins_load(flow_link):
    _editor, link, _gr_link = flow_link
    assert Link.deserialize(link.stage, link.serialize()).pins == []


def test_pins_survive_a_save_and_load(stage_editor, flow_link, tmp_path):
    _editor, link, _gr_link = flow_link
    link.pins = [PIN_A]
    path = tmp_path / "pins.nyx"
    link.stage.export_json(path)

    loaded = Stage()
    loaded.import_json(path)
    (loaded_link,) = [o for o in loaded.uuid_map.values() if isinstance(o, Link)]
    assert loaded_link.pins == [PIN_A]


def test_pin_command_undoes(flow_link):
    _editor, link, _gr_link = flow_link
    stage = link.stage
    stage.push_command(commands.SetLinkPinsCommand(stage, link, [PIN_A]))
    assert link.pins == [PIN_A]
    stage.undo_stack.undo()
    assert link.pins == []
    stage.undo_stack.redo()
    assert link.pins == [PIN_A]


# ======== Editor ========= #


def test_graphics_link_follows_the_stage_pins(flow_link):
    editor, link, _gr_link = flow_link
    link.stage.push_command(
        commands.SetLinkPinsCommand(link.stage, link, [PIN_A, PIN_B])
    )
    gr_link = current_gr_link(editor, link)
    assert gr_link.pins == [PIN_A, PIN_B]
    assert PIN_A in path_points(gr_link.path())
    link.stage.undo_stack.undo()
    assert current_gr_link(editor, link).pins == []


def test_adding_a_pin_pushes_one_command(flow_link):
    editor, link, gr_link = flow_link
    count = link.stage.undo_stack.count()
    gr_link.add_pin(PIN_A)
    assert link.pins == [PIN_A]
    assert link.stage.undo_stack.count() == count + 1
    assert current_gr_link(editor, link).pins == [PIN_A]


def test_moving_a_pin_is_pushed_when_released(flow_link):
    editor, link, gr_link = flow_link
    gr_link.add_pin(PIN_A)
    gr_link = current_gr_link(editor, link)
    (pin,) = [c for c in gr_link.childItems() if isinstance(c, GraphicsLinkPin)]
    pin.setPos(PIN_B)
    assert link.pins == [PIN_A]  # the stage waits for the release
    assert PIN_B in path_points(gr_link.path())
    gr_link.commit_pins()
    assert link.pins == [PIN_B]
    assert current_gr_link(editor, link).pins == [PIN_B]


def test_removing_a_pin(flow_link):
    editor, link, gr_link = flow_link
    gr_link.add_pin(PIN_A)
    gr_link = current_gr_link(editor, link)
    (pin,) = [c for c in gr_link.childItems() if isinstance(c, GraphicsLinkPin)]
    gr_link.remove_pin(pin)
    assert link.pins == []
    gr_link = current_gr_link(editor, link)
    assert gr_link.pins == []
    assert not [c for c in gr_link.childItems() if isinstance(c, GraphicsLinkPin)]


def test_rebuilt_scene_draws_the_saved_pins(flow_link):
    editor, link, _gr_link = flow_link
    link.stage.push_command(commands.SetLinkPinsCommand(link.stage, link, [PIN_A]))
    gr_stage = editor.gr_stage
    gr_stage.remove_link(link)
    plugs = {p.uuid: p for n in gr_stage.gr_nodes() for p in n.plugs}
    gr_link = gr_stage.add_link(link, plugs[link.source], plugs[link.target])
    assert gr_link.pins == [PIN_A]


def test_double_clicking_a_link_pins_it_and_double_clicking_the_pin_removes_it(
    qtbot, flow_link
):
    editor, link, _gr_link = flow_link
    link.target_node.set_position(QtCore.QPointF(600.0, 300.0))
    editor.gr_stage.rebuild_current_scope()
    gr_link = current_gr_link(editor, link)
    view = editor.gr_view
    view.show()
    qtbot.waitExposed(view)
    mid = gr_link.path().pointAtPercent(0.5)
    point = view.mapFromScene(mid)

    qtbot.mouseDClick(view.viewport(), QtCore.Qt.MouseButton.LeftButton, pos=point)
    assert len(link.pins) == 1
    assert (link.pins[0] - mid).manhattanLength() < 8

    point = view.mapFromScene(link.pins[0])
    qtbot.mouseDClick(view.viewport(), QtCore.Qt.MouseButton.LeftButton, pos=point)
    assert link.pins == []


def test_dragging_a_pin_with_the_mouse_moves_it_in_the_stage(qtbot, flow_link):
    editor, link, _gr_link = flow_link
    link.target_node.set_position(QtCore.QPointF(600.0, 300.0))
    link.stage.push_command(
        commands.SetLinkPinsCommand(link.stage, link, [QtCore.QPointF(300.0, 0.0)])
    )
    view = editor.gr_view
    view.show()
    qtbot.waitExposed(view)
    start = view.mapFromScene(QtCore.QPointF(300.0, 0.0))
    end = start + QtCore.QPoint(0, 60)

    QtTest.QTest.mousePress(view.viewport(), QtCore.Qt.MouseButton.LeftButton, pos=start)
    QtTest.QTest.mouseMove(view.viewport(), end)
    QtTest.QTest.mouseRelease(view.viewport(), QtCore.Qt.MouseButton.LeftButton, pos=end)

    (pin,) = link.pins
    assert (pin - view.mapToScene(end)).manhattanLength() < 8
    link.stage.undo_stack.undo()
    assert link.pins == [QtCore.QPointF(300.0, 0.0)]


def test_pins_on_a_gradient_link_take_the_source_color(stage_editor, create_node):
    stage = stage_editor.stage
    getter = create_node(stage, "getter", type_id=CoreNodes.GET)
    setter = create_node(stage, "setter", type_id=CoreNodes.SET)
    stage.push_command(
        commands.LinkNodeComponentsCommand(
            stage=stage, source=getter["value"], target=setter["value"]
        )
    )
    (gr_link,) = stage_editor.gr_stage.gr_links()
    gr_link.add_pin(PIN_A)
    gr_link = stage_editor.gr_stage.get_gr_link(gr_link.uuid)
    (pin,) = [c for c in gr_link.childItems() if isinstance(c, GraphicsLinkPin)]
    assert pin.brush().color() == gr_link.style_plug.color
    assert pin.brush().color() != QtGui.QColor("black")


def test_undoing_an_unlink_brings_the_pins_back(flow_link):
    editor, link, _gr_link = flow_link
    stage = link.stage
    stage.push_command(commands.SetLinkPinsCommand(stage, link, [PIN_A, PIN_B]))
    stage.push_command(commands.UnlinkNodeComponentsCommand(stage, [link.uuid]))
    stage.undo_stack.undo()

    restored = stage.get_object(link.uuid)
    assert restored.pins == [PIN_A, PIN_B]
    assert current_gr_link(editor, restored).pins == [PIN_A, PIN_B]


def test_undoing_a_node_delete_brings_the_pins_back(flow_link):
    _editor, link, _gr_link = flow_link
    stage = link.stage
    stage.push_command(commands.SetLinkPinsCommand(stage, link, [PIN_A]))
    stage.push_command(commands.DeleteNodeCommand(stage, [link.target_node]))
    stage.undo_stack.undo()

    (restored,) = [o for o in stage.uuid_map.values() if isinstance(o, Link)]
    assert restored.pins == [PIN_A]
