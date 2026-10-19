import pytest
from PySide6 import QtGui

from nyx.api.v1 import CoreNodes, DatatypeColor, NodeComponent, commands
from nyx.editor.graphics.graphics_link import GraphicsLink

FLOW = QtGui.QColor(DatatypeColor.FLOW)
DEFAULT = QtGui.QColor(NodeComponent.DEFAULT_PLUG_COLOR)


def link(stage, source, target):
    stage.push_command(
        commands.LinkNodeComponentsCommand(stage=stage, source=source, target=target)
    )


@pytest.fixture
def flow_link(stage_editor, create_node):
    stage = stage_editor.stage
    a = create_node(stage, "a", type_id=CoreNodes.ACTION)
    b = create_node(stage, "b", type_id=CoreNodes.ACTION)
    link(stage, a["flow"], b["flow"])
    (gr_link,) = stage_editor.gr_stage.gr_links()
    return stage_editor, a, b, gr_link


@pytest.fixture
def value_link(stage_editor, create_node):
    stage = stage_editor.stage
    getter = create_node(stage, "getter", type_id=CoreNodes.GET)
    setter = create_node(stage, "setter", type_id=CoreNodes.SET)
    link(stage, getter["value"], setter["value"])
    (gr_link,) = stage_editor.gr_stage.gr_links()
    return stage_editor, getter, setter, gr_link


# ======== Component hook ========= #


def test_components_default_to_the_base_link_width(value_link):
    _editor, getter, _setter, _gr_link = value_link
    assert getter["value"].get_link_width_multiplier() == 1.0


def test_flow_links_are_thicker(flow_link):
    _editor, a, _b, _gr_link = flow_link
    assert a["flow"].get_link_width_multiplier() > 1.0
    assert a["flow"].get_link_width_multiplier() == 2.0
    assert type(a["flow"]).get_link_width_multiplier() == 2.0  # a class method


# ======== Links ========= #


def test_flow_link_takes_the_color_of_its_source(flow_link):
    _editor, _a, _b, gr_link = flow_link
    assert gr_link.pen().color() == FLOW


def test_value_link_takes_the_color_of_its_source(value_link):
    _editor, getter, _setter, gr_link = value_link
    assert gr_link.pen().color() == getter["value"].get_plug_color()
    assert gr_link.pen().color() == DEFAULT  # the source has no typed value yet


def test_value_link_color_follows_the_type_of_the_source_value(value_link):
    editor, getter, setter, gr_link = value_link
    assert gr_link.pen().color() == DEFAULT

    # The getter's value is worked out from what it points at, so use a plain source
    stage = editor.stage
    source_node = stage.get_object(getter.path)
    command = commands.AddNodeComponentCommand(
        node=source_node, type_id="core:value", name="text"
    )
    stage.push_command(command)
    text = command.result_component
    text.produces_output = True
    text.push_value("hello", evaluate=False)
    setter_value = setter["value"]
    setter_value.accepts_input = True
    link(stage, text, setter_value)  # replaces the link into the setter's value

    colors = {link_.pen().color().name() for link_ in editor.gr_stage.gr_links()}
    assert colors == {QtGui.QColor(DatatypeColor.STRING).name()}


def test_link_width_is_scaled_by_its_source(flow_link):
    _editor, _a, _b, gr_link = flow_link
    assert gr_link.pen().widthF() == GraphicsLink.WIDTH * 2.0


def test_default_link_keeps_the_base_width(value_link):
    _editor, _getter, _setter, gr_link = value_link
    assert gr_link.pen().widthF() == GraphicsLink.WIDTH


def test_link_follows_the_source_not_the_target(stage_editor, create_node):
    """A value linked into a plug of another color still comes out in its own."""
    stage = stage_editor.stage
    getter = create_node(stage, "getter", type_id=CoreNodes.GET)
    setter = create_node(stage, "setter", type_id=CoreNodes.SET)
    setter["value"].get_plug_color = lambda: QtGui.QColor("#00ff00")
    stage_editor.gr_stage.rebuild_current_scope()
    link(stage, getter["value"], setter["value"])

    (gr_link,) = stage_editor.gr_stage.gr_links()
    assert gr_link.source_plug.component is getter["value"]
    assert gr_link.pen().color() == getter["value"].get_plug_color()
    assert gr_link.pen().color() != QtGui.QColor("#00ff00")


def test_link_restyles_when_the_source_changes(value_link, monkeypatch):
    editor, getter, _setter, gr_link = value_link
    source_plug = gr_link.source_plug
    monkeypatch.setattr(
        getter["value"], "get_plug_color", lambda: QtGui.QColor("#ff0000")
    )
    monkeypatch.setattr(
        type(getter["value"]), "get_link_width_multiplier", classmethod(lambda c: 3.0)
    )

    source_plug.refresh()

    assert gr_link.pen().color() == QtGui.QColor("#ff0000")
    assert gr_link.pen().widthF() == GraphicsLink.WIDTH * 3.0


def test_link_stays_styled_after_the_scene_is_rebuilt(flow_link):
    editor, _a, _b, _gr_link = flow_link
    editor.gr_stage.rebuild_current_scope()
    (gr_link,) = editor.gr_stage.gr_links()
    assert gr_link.pen().color() == FLOW
    assert gr_link.pen().widthF() == GraphicsLink.WIDTH * 2.0


def test_thick_link_is_not_clipped(flow_link):
    _editor, _a, _b, gr_link = flow_link
    path_bounds = gr_link.path().boundingRect()
    assert gr_link.boundingRect().width() >= path_bounds.width() + GraphicsLink.WIDTH


# ======== Previews ========= #


def test_preview_from_output_socket_looks_like_the_plug_dimmed(
    stage_editor, create_node
):
    stage = stage_editor.stage
    a = create_node(stage, "a", type_id=CoreNodes.ACTION)
    plug = stage_editor.gr_stage.get_gr_node(a).get_plug(a["flow"])

    stage_editor.gr_stage.begin_link_drag(plug, plug.Socket.OUTPUT)
    preview = stage_editor.gr_stage.link_drag_handler.preview

    assert preview.is_preview
    color = preview.pen().color()
    assert (color.red(), color.green(), color.blue()) == (255, 255, 255)
    assert color.alphaF() == pytest.approx(GraphicsLink.PREVIEW_OPACITY, abs=0.01)
    assert preview.pen().widthF() == GraphicsLink.WIDTH * 2.0
    stage_editor.gr_stage.cancel_link_drag()


def test_preview_from_input_socket_looks_like_the_dragged_plug(
    stage_editor, create_node
):
    stage = stage_editor.stage
    setter = create_node(stage, "setter", type_id=CoreNodes.SET)
    plug = stage_editor.gr_stage.get_gr_node(setter).get_plug(setter["value"])

    stage_editor.gr_stage.begin_link_drag(plug, plug.Socket.INPUT)
    preview = stage_editor.gr_stage.link_drag_handler.preview

    assert preview.style_plug is plug
    color = preview.pen().color()
    expected = plug.color
    assert (color.red(), color.green(), color.blue()) == (
        expected.red(),
        expected.green(),
        expected.blue(),
    )
    assert preview.pen().widthF() == GraphicsLink.WIDTH
    stage_editor.gr_stage.cancel_link_drag()


def test_picked_up_link_preview_keeps_the_style_of_its_source(flow_link):
    editor, _a, b, gr_link = flow_link
    target_plug = gr_link.target_plug

    editor.gr_stage.begin_link_drag(target_plug, target_plug.Socket.INPUT)
    preview = editor.gr_stage.link_drag_handler.preview

    assert preview.style_plug is gr_link.source_plug
    assert preview.pen().widthF() == GraphicsLink.WIDTH * 2.0
    editor.gr_stage.cancel_link_drag()


def test_link_without_any_plug_falls_back_to_the_base_look(qapp):
    preview = GraphicsLink()
    color = preview.pen().color()
    assert (color.red(), color.green(), color.blue()) == (
        DEFAULT.red(),
        DEFAULT.green(),
        DEFAULT.blue(),
    )
    assert preview.pen().widthF() == GraphicsLink.WIDTH
