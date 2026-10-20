import pytest
from PySide6 import QtCore, QtGui, QtWidgets

from nyx.api.v1 import CoreNodes, commands
from nyx.editor.graphics.graphics_plug import GraphicsPlug
from nyx.editor.graphics.animation.pulse_animation import PulseAnimation
from nyx.editor.graphics.level_of_detail import (
    MIN_SHAPE_SIZE,
    MIN_TEXT_SIZE,
    LevelOfDetail,
)

FULL_SCALE = 1.0
NO_TEXT_SCALE = 0.35  # sockets are big enough, 10pt text is not
MINIMAL_SCALE = 0.1


def render(item, size, scale) -> QtGui.QImage:
    """Paint an item scaled, on a transparent image of `size` scene units."""
    image = QtGui.QImage(
        int(size.width() * scale) + 1,
        int(size.height() * scale) + 1,
        QtGui.QImage.Format.Format_ARGB32,
    )
    image.fill(QtCore.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(image)
    painter.scale(scale, scale)
    item.paint(painter, QtWidgets.QStyleOptionGraphicsItem(), None)
    painter.end()
    return image


def has_pixels(image, rect: QtCore.QRect) -> bool:
    return any(
        image.pixelColor(x, y).alpha() > 0
        for x in range(rect.left(), min(rect.right(), image.width() - 1) + 1)
        for y in range(rect.top(), min(rect.bottom(), image.height() - 1) + 1)
    )


# ======== Helper ========= #


def test_levels_are_ordered():
    assert LevelOfDetail.MINIMAL < LevelOfDetail.NO_TEXT < LevelOfDetail.FULL


def test_what_each_level_shows():
    assert not LevelOfDetail.MINIMAL.shows_shapes
    assert not LevelOfDetail.MINIMAL.shows_text
    assert LevelOfDetail.NO_TEXT.shows_shapes
    assert not LevelOfDetail.NO_TEXT.shows_text
    assert LevelOfDetail.FULL.shows_shapes
    assert LevelOfDetail.FULL.shows_text


def test_level_follows_the_size_on_screen():
    text, shape = 10.0, 20.0

    assert LevelOfDetail.from_scale(1.0, text, shape) is LevelOfDetail.FULL
    just_text = MIN_TEXT_SIZE / text
    assert LevelOfDetail.from_scale(just_text, text, shape) is LevelOfDetail.FULL
    assert LevelOfDetail.from_scale(just_text * 0.9, text, shape) is (
        LevelOfDetail.NO_TEXT
    )
    just_shape = MIN_SHAPE_SIZE / shape
    assert LevelOfDetail.from_scale(just_shape * 0.9, text, shape) is (
        LevelOfDetail.MINIMAL
    )


def test_missing_sizes_never_limit_the_level():
    assert LevelOfDetail.from_scale(0.001) is LevelOfDetail.FULL
    assert LevelOfDetail.from_scale(0.001, text_size=10.0) is LevelOfDetail.NO_TEXT
    assert LevelOfDetail.from_scale(0.001, shape_size=10.0) is LevelOfDetail.MINIMAL


def test_level_from_painter_uses_its_transform():
    image = QtGui.QImage(10, 10, QtGui.QImage.Format.Format_ARGB32)
    painter = QtGui.QPainter(image)
    painter.scale(0.1, 0.1)

    level = LevelOfDetail.from_painter(painter, text_size=10.0, shape_size=20.0)
    painter.end()

    assert level is LevelOfDetail.MINIMAL


# ======== Plug ========= #


@pytest.fixture
def setter_plug(stage_editor, create_node):
    """Plug with an input socket on the left and its label to the right of it."""
    setter = create_node(stage_editor.stage, "setter", type_id=CoreNodes.SET)
    return stage_editor.gr_stage.get_gr_node(setter).get_plug(setter["value"])


def socket_rect(scale) -> QtCore.QRect:
    center = GraphicsPlug.SOCKET_INSET * scale
    return QtCore.QRect(int(center) - 1, 0, 3, int(GraphicsPlug.ROW_HEIGHT * scale))


def label_rect(plug, scale) -> QtCore.QRect:
    left, _right = plug._label_margins()
    return QtCore.QRect(
        int(left * scale), 0, int(plug.preferred_width() * scale), int(20 * scale)
    )


def test_plug_draws_sockets_and_label_when_big(setter_plug):
    image = render(setter_plug, setter_plug.boundingRect().size(), FULL_SCALE)

    assert has_pixels(image, socket_rect(FULL_SCALE))
    assert has_pixels(image, label_rect(setter_plug, FULL_SCALE))


def test_plug_drops_the_label_before_the_sockets(setter_plug):
    image = render(setter_plug, setter_plug.boundingRect().size(), NO_TEXT_SCALE)

    assert has_pixels(image, socket_rect(NO_TEXT_SCALE))
    assert not has_pixels(image, label_rect(setter_plug, NO_TEXT_SCALE))


def test_plug_draws_nothing_when_tiny(setter_plug):
    image = render(setter_plug, setter_plug.boundingRect().size(), MINIMAL_SCALE)

    assert not has_pixels(image, image.rect())


def test_plug_sockets_cannot_be_grabbed_when_not_drawn(setter_plug):
    scene_pos = setter_plug.mapToScene(GraphicsPlug.SOCKET_INSET, 10)
    render(setter_plug, setter_plug.boundingRect().size(), FULL_SCALE)
    assert setter_plug.socket_at(scene_pos) is GraphicsPlug.Socket.INPUT

    render(setter_plug, setter_plug.boundingRect().size(), MINIMAL_SCALE)

    assert setter_plug.socket_at(scene_pos) is None


# ======== Title and subtitle ========= #


def test_node_text_is_drawn_only_when_readable(stage_editor, create_node):
    node = create_node(stage_editor.stage, "titled", type_id=CoreNodes.ACTION)
    title = stage_editor.gr_stage.get_gr_node(node).title_item
    size = title.boundingRect().size()

    assert has_pixels(render(title, size, FULL_SCALE), QtCore.QRect(0, 0, 80, 20))
    assert not has_pixels(render(title, size, NO_TEXT_SCALE), QtCore.QRect(0, 0, 80, 20))


def test_subtitle_is_drawn_only_when_readable(stage_editor, create_node):
    node = create_node(stage_editor.stage, "titled", type_id=CoreNodes.ACTION)
    node.subtitle = "some subtitle"
    subtitle = stage_editor.gr_stage.get_gr_node(node).subtitle_item
    size = subtitle.boundingRect().size()

    assert has_pixels(render(subtitle, size, FULL_SCALE), QtCore.QRect(0, 0, 60, 10))
    assert not has_pixels(render(subtitle, size, 0.4), QtCore.QRect(0, 0, 60, 10))


# ======== Node ========= #


def test_node_is_a_flat_rect_when_tiny(stage_editor, create_node):
    node = create_node(stage_editor.stage, "box", type_id=CoreNodes.ACTION)
    gr_node = stage_editor.gr_stage.get_gr_node(node)
    size = gr_node.boundingRect().size()

    detailed = render(gr_node, size, FULL_SCALE)
    flat = render(gr_node, size, MINIMAL_SCALE)

    # Rounded corners leave the corner pixel empty, the placeholder fills it.
    assert detailed.pixelColor(1, 1).alpha() == 0
    assert flat.pixelColor(0, 0).alpha() > 0


# ======== Link ========= #


@pytest.fixture
def pulsing_link(stage_editor, create_node):
    stage = stage_editor.stage
    start = create_node(stage, "start", type_id=CoreNodes.FLOW_START)
    action = create_node(stage, "action", type_id=CoreNodes.ACTION)
    stage.push_command(
        commands.LinkNodeComponentsCommand(
            stage=stage, source=start["flow"], target=action["flow"]
        )
    )
    gr_link = next(
        link
        for link in stage_editor.gr_stage.gr_links()
        if link.has_animation(PulseAnimation)
    )
    gr_link.get_animation(PulseAnimation).offset = 40.0
    return gr_link


def has_pulse_color(image) -> bool:
    pulse = PulseAnimation().color.rgb()
    return any(
        image.pixel(x, y) == pulse
        for x in range(image.width())
        for y in range(image.height())
    )


def render_link(gr_link, scale) -> QtGui.QImage:
    rect = gr_link.boundingRect().toAlignedRect()
    image = QtGui.QImage(
        int(rect.width() * scale) + 1,
        int(rect.height() * scale) + 1,
        QtGui.QImage.Format.Format_ARGB32,
    )
    image.fill(QtCore.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(image)
    painter.scale(scale, scale)
    painter.translate(-rect.topLeft())
    gr_link.paint(painter, QtWidgets.QStyleOptionGraphicsItem(), None)
    painter.end()
    return image


def test_pulse_is_drawn_when_the_link_is_big_enough(pulsing_link):
    assert has_pulse_color(render_link(pulsing_link, FULL_SCALE))


def test_pulse_is_skipped_when_the_link_is_tiny(pulsing_link):
    image = render_link(pulsing_link, MINIMAL_SCALE)

    assert not has_pulse_color(image)
    assert has_pixels(image, image.rect())  # the link itself is still drawn


def test_pulse_stops_ticking_when_zoomed_far_out(stage_editor, pulsing_link):
    gr_stage = stage_editor.gr_stage
    view = stage_editor.gr_view

    view.setTransform(QtGui.QTransform.fromScale(FULL_SCALE, FULL_SCALE))
    assert bool(gr_stage.link_animator.active_links()) == view.isVisible()

    view.setTransform(QtGui.QTransform.fromScale(MINIMAL_SCALE, MINIMAL_SCALE))
    assert not gr_stage.link_animator.active_links()
