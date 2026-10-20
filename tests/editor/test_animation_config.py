import json

import pytest
from PySide6 import QtGui

from nyx.core.config_values.animation_values import (
    NyxEditorLinkGlowAnimationConfigValues,
    NyxEditorLinkPulseAnimationConfigValues,
)
from nyx.core.config_values.root_values import NyxConfigValues
from nyx.editor.graphics.animation.glow_animation import MIN_PERIOD, GlowAnimation
from nyx.editor.graphics.animation.pulse_animation import PulseAnimation


@pytest.fixture
def animation_config(main_window):
    """Animation values of the live config, restored after the test."""
    animations = main_window.config.values.editor_style.animations
    saved = (animations.link_pulse.model_copy(), animations.link_glow.model_copy())
    yield animations
    animations.link_pulse, animations.link_glow = saved


# ======== Defaults ========= #


def test_default_colors_are_valid():
    animations = NyxConfigValues().editor_style.animations

    assert QtGui.QColor(animations.link_pulse.color).isValid()
    assert QtGui.QColor(animations.link_glow.color).isValid()


def test_default_pulse_values():
    pulse = NyxEditorLinkPulseAnimationConfigValues()

    assert pulse.color == "#4BE3FF"
    assert pulse.speed > 0
    assert pulse.radius > 0
    assert pulse.tail_samples >= 1
    assert pulse.tail_step > 0


def test_default_glow_layers_are_wide_to_narrow_and_get_stronger():
    glow = NyxEditorLinkGlowAnimationConfigValues()

    assert glow.layers == ((12.0, 0.15), (8.0, 0.25), (4.0, 0.4))
    widths = [width for width, _opacity in glow.layers]
    opacities = [opacity for _width, opacity in glow.layers]
    assert widths == sorted(widths, reverse=True)
    assert opacities == sorted(opacities)
    assert all(0.0 < opacity <= 1.0 for opacity in opacities)
    assert glow.period > 0


def test_glow_layers_survive_a_json_round_trip():
    glow = NyxEditorLinkGlowAnimationConfigValues()

    loaded = glow.replace(json.loads(json.dumps(glow.to_dict())))

    # Files give lists, the animation reads both.
    assert [tuple(layer) for layer in loaded.layers] == list(glow.layers)
    assert GlowAnimation(loaded).layers == GlowAnimation(glow).layers


# ======== Pulse ========= #


def test_pulse_takes_its_values_from_the_config():
    config = NyxEditorLinkPulseAnimationConfigValues(
        color="#ff0000", speed=50.0, radius=8, tail_samples=3, tail_step=2.0
    )

    pulse = PulseAnimation(config)

    assert pulse.color == QtGui.QColor("#ff0000")
    assert pulse.speed == 50.0
    assert pulse.radius == 8
    assert pulse.tail_samples == 3
    assert pulse.tail_step == 2.0
    assert pulse.SHAPE_SIZE == 16
    assert pulse.MARGIN == 8


def test_pulse_moves_at_the_configured_speed():
    pulse = PulseAnimation(NyxEditorLinkPulseAnimationConfigValues(speed=10.0))

    pulse.advance(3.0)

    assert pulse.offset == pytest.approx(30.0)


def test_pulse_uses_the_application_config_by_default(animation_config):
    animation_config.link_pulse.color = "#00ff00"
    animation_config.link_pulse.speed = 77.0

    pulse = PulseAnimation()

    assert pulse.color == QtGui.QColor("#00ff00")
    assert pulse.speed == 77.0


def test_pulse_with_a_bad_color_uses_the_default_color(caplog):
    with caplog.at_level("WARNING"):
        pulse = PulseAnimation(NyxEditorLinkPulseAnimationConfigValues(color="#4BEFF"))

    assert pulse.color == QtGui.QColor("#4BE3FF")
    assert "Invalid animation color '#4BEFF'" in caplog.text


def test_pulse_tail_has_at_least_one_dot():
    pulse = PulseAnimation(NyxEditorLinkPulseAnimationConfigValues(tail_samples=0))

    assert pulse.tail_samples == 1


# ======== Glow ========= #


def test_glow_takes_its_values_from_the_config():
    config = NyxEditorLinkGlowAnimationConfigValues(
        color="#00ff00", period=3.0, layers=((10.0, 0.5), (2.0, 1.0))
    )

    glow = GlowAnimation(config)

    assert glow.color == QtGui.QColor("#00ff00")
    assert glow.period == 3.0
    assert glow.layers == [(10.0, 0.5), (2.0, 1.0)]
    assert glow.SHAPE_SIZE == 10.0
    assert glow.MARGIN == 5.0


def test_glow_is_sized_by_its_widest_layer():
    narrow = GlowAnimation(NyxEditorLinkGlowAnimationConfigValues(layers=((2.0, 1.0),)))
    wide = GlowAnimation(NyxEditorLinkGlowAnimationConfigValues(layers=((20.0, 1.0),)))

    assert narrow.MARGIN < wide.MARGIN
    assert wide.SHAPE_SIZE == 20.0


def test_glow_uses_the_application_config_by_default(animation_config):
    animation_config.link_glow.period = 9.0

    assert GlowAnimation().period == 9.0


def test_glow_layers_are_drawn_from_the_widest_and_clamped():
    config = NyxEditorLinkGlowAnimationConfigValues(
        layers=((2.0, 0.9), (9.0, 5.0), (4.0, -1.0))
    )

    glow = GlowAnimation(config)

    assert glow.layers == [(9.0, 1.0), (4.0, 0.0), (2.0, 0.9)]


def test_glow_accepts_layers_as_lists_like_a_config_file_gives(caplog):
    config = NyxEditorLinkGlowAnimationConfigValues().replace(
        {"layers": [[6, 0.5], [3, 0.25]]}
    )

    assert GlowAnimation(config).layers == [(6.0, 0.5), (3.0, 0.25)]


def test_glow_ignores_layers_that_are_not_usable(caplog):
    config = NyxEditorLinkGlowAnimationConfigValues().replace(
        {"layers": [[6, 0.5], [3], "x", [0, 1.0], [-2, 1.0], [5, "a"]]}
    )

    with caplog.at_level("WARNING"):
        glow = GlowAnimation(config)

    assert glow.layers == [(6.0, 0.5)]
    assert "Ignoring invalid glow layer" in caplog.text


def test_glow_without_layers_is_never_drawn_or_seen():
    glow = GlowAnimation(NyxEditorLinkGlowAnimationConfigValues(layers=()))

    assert glow.layers == []
    assert glow.SHAPE_SIZE == 0.0
    assert glow.MARGIN == 0.0
    assert not glow.is_visible_at(1.0)


def test_glow_period_can_not_be_zero():
    glow = GlowAnimation(NyxEditorLinkGlowAnimationConfigValues(period=0.0))

    glow.advance(1.0)  # must not divide by zero

    assert glow.period == MIN_PERIOD
    assert 0.0 <= glow.intensity <= 1.0


def test_glow_with_a_bad_color_uses_the_default_color(caplog):
    with caplog.at_level("WARNING"):
        glow = GlowAnimation(NyxEditorLinkGlowAnimationConfigValues(color="nope"))

    assert glow.color == QtGui.QColor("#4BE3FF")
