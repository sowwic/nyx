import pytest
from PySide6 import QtCore, QtGui, QtWidgets

from nyx.api.v1 import (
    CoreNodeComponents,
    CoreNodes,
    GraphicsPlugShape,
    NodeComponent,
    commands,
)
from nyx.editor.graphics.graphics_plug import GraphicsPlug
from nyx.editor.graphics.graphics_plug_shape import (
    PLUG_SHAPES,
    BarsPlugShape,
    CirclePlugShape,
    DiamondPlugShape,
    SquareMatrixPlugShape,
    PlugShape,
    TrianglePlugShape,
    plug_shape_for,
)

SAMPLE = QtGui.QColor("#FFA637")  # any color, the shapes draw what they are given
WHITE = QtGui.QColor("#ffffff")
FLOW = QtGui.QColor("#FFFFFF")
DEFAULT = QtGui.QColor(NodeComponent.DEFAULT_PLUG_COLOR)
CENTER = QtCore.QPointF(20.0, 15.0)


def render(draw, size=(40, 30), antialiasing=False):
    """Paint with `draw(painter)` on a transparent image."""
    image = QtGui.QImage(*size, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtCore.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(image)
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, antialiasing)
    draw(painter)
    painter.end()
    return image


def pixel(image, x, y) -> str:
    """Color of a pixel as #aarrggbb."""
    return image.pixelColor(x, y).name(QtGui.QColor.NameFormat.HexArgb)


TRANSPARENT = "#00000000"


def paint_shape(shape, color=SAMPLE, linked=False):
    return render(lambda painter: shape.paint(painter, CENTER, color, linked))


# ======== Shapes ========= #


def test_shapes_are_plug_shapes_and_base_cannot_be_drawn():
    assert isinstance(CirclePlugShape(), PlugShape)
    assert isinstance(TrianglePlugShape(), PlugShape)
    with pytest.raises(TypeError):
        PlugShape()


def test_circle_is_filled_with_a_hole_until_linked():
    unlinked = paint_shape(CirclePlugShape(), linked=False)
    assert pixel(unlinked, 20, 15) == QtGui.QColor("black").name(
        QtGui.QColor.NameFormat.HexArgb
    )  # the hole
    assert pixel(unlinked, 24, 15) == SAMPLE.name(QtGui.QColor.NameFormat.HexArgb)
    assert pixel(unlinked, 28, 15) == TRANSPARENT  # outside of the circle

    linked = paint_shape(CirclePlugShape(), linked=True)
    assert pixel(linked, 20, 15) == SAMPLE.name(QtGui.QColor.NameFormat.HexArgb)
    assert pixel(linked, 28, 15) == TRANSPARENT


def test_circle_uses_the_given_color():
    image = paint_shape(CirclePlugShape(), color=QtGui.QColor("#12ab34"), linked=True)
    assert pixel(image, 20, 15) == "#ff12ab34"


def test_bars_miss_the_middle_bar_until_linked():
    sample = SAMPLE.name(QtGui.QColor.NameFormat.HexArgb)
    unlinked = paint_shape(BarsPlugShape(), linked=False)
    assert pixel(unlinked, 20, 11) == sample  # top bar
    assert pixel(unlinked, 20, 15) == TRANSPARENT  # no middle bar
    assert pixel(unlinked, 20, 19) == sample  # bottom bar

    linked = paint_shape(BarsPlugShape(), linked=True)
    assert pixel(linked, 20, 11) == sample
    assert pixel(linked, 20, 15) == sample
    assert pixel(linked, 20, 19) == sample
    assert pixel(linked, 12, 15) == TRANSPARENT  # left of the bars
    assert pixel(linked, 28, 15) == TRANSPARENT  # right of the bars


def test_diamond_has_a_hole_until_linked():
    sample = SAMPLE.name(QtGui.QColor.NameFormat.HexArgb)
    black = QtGui.QColor("black").name(QtGui.QColor.NameFormat.HexArgb)
    unlinked = paint_shape(DiamondPlugShape(), linked=False)
    assert pixel(unlinked, 20, 15) == black  # the hole
    assert pixel(unlinked, 20, 11) == sample
    assert pixel(unlinked, 25, 11) == TRANSPARENT  # empty corner of the box

    linked = paint_shape(DiamondPlugShape(), linked=True)
    assert pixel(linked, 20, 15) == sample
    assert pixel(linked, 25, 11) == TRANSPARENT


def test_triangle_is_outlined_until_linked():
    white = WHITE.name(QtGui.QColor.NameFormat.HexArgb)
    unlinked = paint_shape(TrianglePlugShape(), color=WHITE, linked=False)
    assert pixel(unlinked, 16, 15) == white  # left edge
    assert pixel(unlinked, 19, 15) == TRANSPARENT  # inside, not filled

    linked = paint_shape(TrianglePlugShape(), color=WHITE, linked=True)
    assert pixel(linked, 16, 15) == white
    assert pixel(linked, 19, 15) == white  # inside, filled


@pytest.mark.parametrize("linked", [True, False])
def test_triangle_points_right_and_keeps_to_its_bounds(linked):
    image = paint_shape(TrianglePlugShape(), color=WHITE, linked=linked)
    assert pixel(image, 13, 15) == TRANSPARENT  # left of the triangle
    assert pixel(image, 24, 11) == TRANSPARENT  # empty corner above the tip
    assert pixel(image, 24, 19) == TRANSPARENT  # empty corner below the tip
    assert pixel(image, 20, 5) == TRANSPARENT  # above
    assert pixel(image, 20, 25) == TRANSPARENT  # below
    # The tip is on the right of the center
    assert pixel(image, 24, 15) != TRANSPARENT


def test_triangle_corners():
    polygon = TrianglePlugShape().polygon(CENTER)
    points = [(point.x(), point.y()) for point in polygon]
    assert points == [(16.0, 10.0), (16.0, 20.0), (25.0, 15.0)]


@pytest.mark.parametrize(
    "shape",
    [CirclePlugShape(), TrianglePlugShape(), BarsPlugShape(), DiamondPlugShape()],
)
def test_shapes_grab_the_socket_within_reach(shape):
    assert shape.contains(QtCore.QPointF(0.0, 0.0))
    assert shape.contains(QtCore.QPointF(shape.HIT_RADIUS - 0.5, 0.0))
    assert not shape.contains(QtCore.QPointF(shape.HIT_RADIUS + 0.5, 0.0))
    assert not shape.contains(QtCore.QPointF(0.0, shape.HIT_RADIUS + 0.5))


def test_every_shape_kind_has_a_drawing():
    for kind in GraphicsPlugShape:
        assert isinstance(PLUG_SHAPES[kind], PlugShape)
    assert isinstance(plug_shape_for(GraphicsPlugShape.CIRCLE), CirclePlugShape)
    assert isinstance(plug_shape_for(GraphicsPlugShape.TRIANGLE), TrianglePlugShape)
    assert isinstance(plug_shape_for(GraphicsPlugShape.BARS), BarsPlugShape)
    assert isinstance(plug_shape_for(GraphicsPlugShape.DIAMOND), DiamondPlugShape)


def test_unknown_shape_kind_falls_back_to_the_circle():
    assert isinstance(plug_shape_for(99), CirclePlugShape)
    assert isinstance(plug_shape_for(None), CirclePlugShape)


# ======== Component hooks ========= #


def test_components_describe_their_plug(qapp):
    from nyx.api.v1 import Stage

    stage = Stage()
    action = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.ACTION)
    stage.push_command(action)
    flow = action.result_node["flow"]
    value_command = commands.AddNodeComponentCommand(
        node=action.result_node, type_id=CoreNodeComponents.VALUE, name="value"
    )
    stage.push_command(value_command)
    value = value_command.result_component

    assert flow.get_plug_shape() is GraphicsPlugShape.PENTAGON
    assert flow.get_plug_color() == FLOW
    assert value.get_plug_shape() is GraphicsPlugShape.SQUARE_MATRIX
    assert value.get_plug_color() == DEFAULT  # no value yet, so no type to go by
    assert isinstance(value.get_plug_color(), QtGui.QColor)


def test_value_plug_color_follows_the_type_of_the_value(qapp):
    from nyx.api.v1 import Stage

    stage = Stage()
    node_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.ACTION)
    stage.push_command(node_command)
    add_command = commands.AddNodeComponentCommand(
        node=node_command.result_node, type_id=CoreNodeComponents.VALUE, name="value"
    )
    stage.push_command(add_command)
    value = add_command.result_component

    value.push_value(True, evaluate=False)
    assert value.get_plug_color() == QtGui.QColor("#FF0000")
    value.push_value("text", evaluate=False)
    assert value.get_plug_color() == QtGui.QColor("#FFA637")
    value.push_value(12, evaluate=False)
    assert value.get_plug_color() == QtGui.QColor("#38D6A4")
    value.push_value([1], evaluate=False)
    assert value.get_plug_color() == QtGui.QColor("#FF5FB0")
    value.push_value({"a": 1}, evaluate=False)
    assert value.get_plug_color() == QtGui.QColor("#FFD84B")
    value.push_value({1}, evaluate=False)  # a type without a datatype of its own
    assert value.get_plug_color() == DEFAULT


def test_comment_plug_color(qapp):
    from nyx.api.v1 import Stage

    stage = Stage()
    node_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.ACTION)
    stage.push_command(node_command)
    add_command = commands.AddNodeComponentCommand(
        node=node_command.result_node, type_id=CoreNodeComponents.COMMENT, name="note"
    )
    stage.push_command(add_command)
    assert add_command.result_component.get_plug_color() == QtGui.QColor("#FFA637")


# ======== Plug ========= #


@pytest.fixture
def plugs(stage_editor, create_node):
    """Flow plug of an action node and value plug of a setter node."""
    stage = stage_editor.stage
    action = create_node(stage, "action", type_id=CoreNodes.ACTION)
    setter = create_node(stage, "setter", type_id=CoreNodes.SET)
    gr_stage = stage_editor.gr_stage
    flow_plug = gr_stage.get_gr_node(action).get_plug(action["flow"])
    value_plug = gr_stage.get_gr_node(setter).get_plug(setter["value"])
    return flow_plug, value_plug


def test_plug_picks_the_shape_and_color_of_its_component(plugs):
    flow_plug, value_plug = plugs
    assert isinstance(flow_plug.shape, TrianglePlugShape)
    assert flow_plug.color == FLOW
    assert isinstance(value_plug.shape, SquareMatrixPlugShape)
    assert value_plug.color == DEFAULT


def test_plug_follows_a_color_change_of_the_component(plugs, monkeypatch):
    _flow_plug, value_plug = plugs
    monkeypatch.setattr(
        value_plug.component, "get_plug_color", lambda: QtGui.QColor("#ff0000")
    )
    value_plug.refresh()
    assert value_plug.color == QtGui.QColor("#ff0000")


def test_plug_follows_a_shape_change_of_the_component(plugs, monkeypatch):
    _flow_plug, value_plug = plugs
    monkeypatch.setattr(
        value_plug.component, "get_plug_shape", lambda: GraphicsPlugShape.TRIANGLE
    )
    value_plug.refresh()
    assert isinstance(value_plug.shape, TrianglePlugShape)


def test_plug_label_keeps_clear_of_the_shape(plugs):
    flow_plug, _value_plug = plugs
    assert flow_plug.shape.RADIUS == TrianglePlugShape.RADIUS


def test_triangle_plug_is_still_grabbed_at_both_ends(plugs):
    flow_plug, _value_plug = plugs  # accepts input and produces output
    assert flow_plug.socket_at(flow_plug.input_anchor()) is GraphicsPlug.Socket.INPUT
    assert flow_plug.socket_at(flow_plug.output_anchor()) is GraphicsPlug.Socket.OUTPUT
    middle = flow_plug.mapToScene(flow_plug.gr_node.width / 2, 10.0)
    assert flow_plug.socket_at(middle) is None


def test_circle_plug_is_grabbed_at_its_input_end(plugs):
    _flow_plug, value_plug = plugs  # input only
    assert value_plug.socket_at(value_plug.input_anchor()) is GraphicsPlug.Socket.INPUT
    assert value_plug.socket_at(value_plug.output_anchor()) is None


def paint_plug(plug):
    width = int(plug.boundingRect().width()) + 4
    option = QtWidgets.QStyleOptionGraphicsItem()

    def draw(painter):
        painter.translate(-plug.boundingRect().left(), 0)
        plug.paint(painter, option, None)

    return render(draw, size=(width, int(plug.ROW_HEIGHT)), antialiasing=True), plug


def test_flow_plug_is_painted_as_pentagon_with_the_component_color(plugs):
    flow_plug, value_plug = plugs
    image, _ = paint_plug(flow_plug)
    left = -flow_plug.boundingRect().left()
    output_x = left + flow_plug.gr_node.width - flow_plug.SOCKET_INSET
    tip_x = int(output_x + 3)  # inside the output pentagon
    # Not linked: only the outline is drawn, white and not the circle's orange.
    on_outline = QtGui.QColor(image.pixelColor(int(output_x - 5), 10))
    assert on_outline.alpha() > 0
    assert (on_outline.red(), on_outline.green(), on_outline.blue()) == (255, 255, 255)
    assert tip_x < image.width()

    image, _ = paint_plug(value_plug)
    input_x = -value_plug.boundingRect().left() + value_plug.SOCKET_INSET
    circle_ring = image.pixelColor(int(input_x + 4), 10)
    # Anti-aliased against the outline, so only check that it is the default blue.
    assert circle_ring.alpha() > 0
    assert circle_ring.blue() > circle_ring.green() > circle_ring.red()
    assert circle_ring.blue() - circle_ring.red() > 80


def hover(plug):
    plug.hoverEnterEvent(QtWidgets.QGraphicsSceneHoverEvent())


def test_plug_shows_the_roles_of_its_component_when_diagnostics_are_on(
    plugs, monkeypatch
):
    _flow_plug, value_plug = plugs
    monkeypatch.setattr(
        "nyx.editor.graphics.graphics_plug.are_hover_diagnostics_enabled", lambda: True
    )

    hover(value_plug)

    tooltip = value_plug.toolTip()
    assert "resolvedDatatype" in tooltip
    assert "core:object" in tooltip
    assert "isValid" in tooltip


def test_plug_shows_the_description_when_diagnostics_are_off(plugs, monkeypatch):
    flow_plug, value_plug = plugs
    monkeypatch.setattr(
        "nyx.editor.graphics.graphics_plug.are_hover_diagnostics_enabled", lambda: False
    )
    value_plug.component.description = "Number to use."

    hover(value_plug)
    hover(flow_plug)

    assert "<td>Number to use.</td>" in value_plug.toolTip()
    assert "isValid" not in value_plug.toolTip()
    # A flow holds no value
    assert flow_plug.component.description in flow_plug.toolTip()
    assert "Value" not in flow_plug.toolTip()


def test_plug_tooltip_follows_a_changed_description(plugs, monkeypatch):
    _flow_plug, value_plug = plugs
    monkeypatch.setattr(
        "nyx.editor.graphics.graphics_plug.are_hover_diagnostics_enabled", lambda: False
    )
    hover(value_plug)
    value_plug.component.description = "New text."

    hover(value_plug)

    assert "New text." in value_plug.toolTip()


def test_plug_tooltip_shows_the_raw_and_cached_value(plugs, monkeypatch):
    _flow_plug, value_plug = plugs
    monkeypatch.setattr(
        "nyx.editor.graphics.graphics_plug.are_hover_diagnostics_enabled", lambda: False
    )
    value_plug.component.push_value("1+1")

    hover(value_plug)

    tooltip = value_plug.toolTip()
    assert "<b>Raw:</b> 1+1<br><b>Cache:</b> 2" in tooltip
    assert tooltip.index("Description") < tooltip.index("Value")
    assert tooltip.index("Raw:") < tooltip.index("Cache:")


def test_plug_tooltip_escapes_and_shortens_values(plugs, monkeypatch):
    _flow_plug, value_plug = plugs
    monkeypatch.setattr(
        "nyx.editor.graphics.graphics_plug.are_hover_diagnostics_enabled", lambda: False
    )
    value_plug.component.push_value("'<b>" + "x" * 500 + "'")

    hover(value_plug)

    tooltip = value_plug.toolTip()
    assert "<b>x" not in tooltip
    assert "&lt;b&gt;" in tooltip
    assert "…" in tooltip


def test_plug_tooltip_follows_the_component(plugs, monkeypatch):
    _flow_plug, value_plug = plugs
    monkeypatch.setattr(
        "nyx.editor.graphics.graphics_plug.are_hover_diagnostics_enabled", lambda: True
    )
    hover(value_plug)
    value_plug.component.set_datatype("core:int")

    hover(value_plug)

    assert "core:int" in value_plug.toolTip()


def test_node_is_wide_enough_for_the_labels_of_its_plugs(stage_editor, create_node):
    from nyx.editor.graphics.graphics_plug import GraphicsPlug  # noqa: F401

    node = create_node(stage_editor.stage, "branch", type_id=CoreNodes.BRANCH)
    gr_node = stage_editor.gr_stage.get_gr_node(node)

    assert gr_node.plugs
    for plug in gr_node.plugs:
        assert plug.preferred_width() <= gr_node.width


def test_long_component_name_widens_the_node(stage_editor, create_node):
    node = create_node(stage_editor.stage, "action", type_id=CoreNodes.ACTION)
    gr_node = stage_editor.gr_stage.get_gr_node(node)
    plain_width = gr_node.width

    stage_editor.stage.push_command(
        commands.RenameNodeComponentCommand(
            stage=stage_editor.stage,
            node_component=node["flow"],
            new_name="a_really_long_component_name_for_a_flow",
        )
    )

    assert gr_node.width > plain_width
    assert gr_node.plugs[0].preferred_width() <= gr_node.width


def test_label_keeps_clear_of_the_sockets(plugs):
    flow_plug, value_plug = plugs
    shape_room = flow_plug.SOCKET_INSET + flow_plug._shape.RADIUS * 2
    left, right = flow_plug._label_margins()  # in and out socket
    assert left > shape_room and right > shape_room

    left, right = value_plug._label_margins()  # input socket only
    assert left > shape_room
    assert right == value_plug.SOCKET_INSET


def test_sockets_are_inside_of_the_node(plugs):
    flow_plug, value_plug = plugs
    node_width = flow_plug.gr_node.width

    assert flow_plug.mapFromScene(flow_plug.input_anchor()).x() == flow_plug.SOCKET_INSET
    assert (
        flow_plug.mapFromScene(flow_plug.output_anchor()).x()
        == node_width - flow_plug.SOCKET_INSET
    )
    assert flow_plug.boundingRect().left() == 0.0
    assert flow_plug.boundingRect().right() == node_width


def test_socket_is_grabbed_at_its_inset_position_only(plugs):
    flow_plug, _value_plug = plugs
    on_edge = flow_plug.mapToScene(0.0, flow_plug.ROW_HEIGHT / 2)
    inset_right = flow_plug.output_anchor()

    assert flow_plug.socket_at(inset_right) is GraphicsPlug.Socket.OUTPUT
    assert flow_plug.socket_at(on_edge) is None  # 10 units away from the socket
