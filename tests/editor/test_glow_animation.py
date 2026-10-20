import pytest
from PySide6 import QtCore, QtGui, QtWidgets

from nyx.api.v1 import CoreNodes, commands
from nyx.editor.graphics.animation.glow_animation import GlowAnimation
from nyx.editor.graphics.animation.pulse_animation import PulseAnimation
from nyx.editor.graphics.graphics_stage import GraphicsStage
from nyx.static.enums import LinkAnimationStyle


@pytest.fixture
def flow_start_link(stage_editor, create_node):
    """The graphics link from a flow start to an action, without animations."""
    stage = stage_editor.stage
    start = create_node(stage, "start", type_id=CoreNodes.FLOW_START)
    action = create_node(stage, "action", type_id=CoreNodes.ACTION)
    stage.push_command(
        commands.LinkNodeComponentsCommand(
            stage=stage, source=start["flow"], target=action["flow"]
        )
    )
    gr_link = stage_editor.gr_stage.gr_links()[0]
    # The chain highlight already animates it, the tests choose their own animations.
    stage_editor.gr_stage.link_animator.unregister(gr_link)
    return stage_editor, gr_link


@pytest.fixture
def stage_config(main_window):
    values = main_window.config.values.editor_widgets.graphics_stage
    saved = (values.highlight_flow_chain, values.highlight_flow_chain_style)
    yield values
    values.highlight_flow_chain, values.highlight_flow_chain_style = saved


def render(draw, gr_link, scale=1.0) -> QtGui.QImage:
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
    draw(painter)
    painter.end()
    return image


def opaque_pixels(image) -> int:
    return sum(
        1
        for x in range(image.width())
        for y in range(image.height())
        if image.pixelColor(x, y).alpha() > 0
    )


def peak_alpha(image) -> int:
    return max(
        image.pixelColor(x, y).alpha()
        for x in range(image.width())
        for y in range(image.height())
    )


# ======== Intensity ========= #


def test_glow_is_hidden_until_advanced():
    assert GlowAnimation().intensity is None


def test_intensity_swells_from_none_to_full_and_back():
    glow = GlowAnimation()

    glow.advance(0.0)
    assert glow.intensity == pytest.approx(0.0)

    glow.advance(glow.period / 2)
    assert glow.intensity == pytest.approx(1.0)

    glow.advance(glow.period)
    assert glow.intensity == pytest.approx(0.0, abs=1e-9)


def test_intensity_stays_between_zero_and_one():
    glow = GlowAnimation()

    for step in range(200):
        glow.advance(step * 0.037)
        assert 0.0 <= glow.intensity <= 1.0


def test_intensity_repeats_every_period():
    glow = GlowAnimation()
    glow.advance(0.4)
    first = glow.intensity

    glow.advance(0.4 + 3 * glow.period)

    assert glow.intensity == pytest.approx(first)


def test_reset_hides_the_glow():
    glow = GlowAnimation()
    glow.advance(0.5)

    glow.reset()

    assert glow.intensity is None


# ======== Painting ========= #


def test_glow_is_drawn_behind_the_stroke_only(flow_start_link):
    _editor, gr_link = flow_start_link
    glow = GlowAnimation()
    glow.advance(glow.period / 2)

    below = render(lambda p: glow.paint_below(p, gr_link), gr_link)
    above = render(lambda p: glow.paint_above(p, gr_link), gr_link)

    assert opaque_pixels(below) > 0
    assert opaque_pixels(above) == 0


def test_hidden_or_zero_glow_draws_nothing(flow_start_link):
    _editor, gr_link = flow_start_link
    glow = GlowAnimation()

    hidden = render(lambda p: glow.paint_below(p, gr_link), gr_link)
    glow.advance(0.0)
    none = render(lambda p: glow.paint_below(p, gr_link), gr_link)

    assert opaque_pixels(hidden) == 0
    assert opaque_pixels(none) == 0


def test_stronger_glow_is_more_opaque(flow_start_link):
    _editor, gr_link = flow_start_link
    glow = GlowAnimation()
    alphas = []
    for fraction in (0.1, 0.25, 0.5):
        glow.advance(glow.period * fraction)
        image = render(lambda p: glow.paint_below(p, gr_link), gr_link)
        alphas.append(peak_alpha(image))

    assert alphas == sorted(alphas)
    assert alphas[0] < alphas[-1]


def test_bounds_leave_room_for_the_glow(flow_start_link):
    _editor, gr_link = flow_start_link
    plain = gr_link.boundingRect()

    gr_link.add_animation(GlowAnimation())
    grown = gr_link.boundingRect()
    gr_link.remove_animation(GlowAnimation)

    assert grown.width() == pytest.approx(plain.width() + 2 * GlowAnimation().MARGIN)
    assert gr_link.boundingRect() == plain


def paint_link(gr_link, scale) -> QtGui.QImage:
    def paint(painter):
        gr_link.paint(painter, QtWidgets.QStyleOptionGraphicsItem(), None)

    return render(paint, gr_link, scale)


def test_link_paints_the_glow_when_big_enough(flow_start_link):
    _editor, gr_link = flow_start_link
    bare = paint_link(gr_link, 1.0)
    glow = GlowAnimation()
    glow.advance(glow.period / 2)
    gr_link.add_animation(glow)

    glowing = paint_link(gr_link, 1.0)

    # The glow is wider than the stroke, so it adds pixels around it.
    assert opaque_pixels(glowing) > opaque_pixels(bare)


def test_link_skips_the_glow_when_too_small_to_see(flow_start_link):
    _editor, gr_link = flow_start_link
    bare = opaque_pixels(paint_link(gr_link, 0.1))
    glow = GlowAnimation()
    glow.advance(glow.period / 2)
    gr_link.add_animation(glow)

    # 12 units at 10% is 1.2 px, below what is worth drawing.
    assert opaque_pixels(paint_link(gr_link, 0.1)) == bare


# ======== Style ========= #


def test_glow_has_its_own_style_value():
    assert LinkAnimationStyle.GLOW == "glow"


def test_the_glow_style_highlights_the_chain_with_glows(flow_start_link, stage_config):
    editor, gr_link = flow_start_link
    stage_config.highlight_flow_chain_style = "glow"

    editor.gr_stage.rebuild_current_scope()

    assert GraphicsStage.get_flow_chain_highlight_style() is LinkAnimationStyle.GLOW
    links = editor.gr_stage.gr_links()
    assert len(links) == 1
    assert links[0].has_animation(GlowAnimation)
    assert not links[0].has_animation(PulseAnimation)


def test_changing_the_style_swaps_the_animation(flow_start_link, stage_config):
    editor, _gr_link = flow_start_link
    stage_config.highlight_flow_chain_style = "glow"
    editor.gr_stage.rebuild_current_scope()

    stage_config.highlight_flow_chain_style = "pulse"
    editor.gr_stage.rebuild_current_scope()

    link = editor.gr_stage.gr_links()[0]
    assert link.has_animation(PulseAnimation)
    assert not link.has_animation(GlowAnimation)
    animator = editor.gr_stage.link_animator
    assert [type(a) for a in animator.animations_of(link)] == [PulseAnimation]
