import pytest
from PySide6 import QtCore

from nyx.editor.views.stage_graph_zoom import StageGraphZoom


def test_default_zoom_is_full_scale():
    zoom = StageGraphZoom()

    assert zoom.zoom == StageGraphZoom.DEFAULT_ZOOM
    assert zoom.scale == pytest.approx(1.0)
    assert zoom.transform.m11() == pytest.approx(1.0)


def test_scale_changes_by_the_factor_per_level():
    zoom = StageGraphZoom()

    assert zoom.scale_for(8) == pytest.approx(1.25**-2)


def test_clamp_limits_to_the_range():
    zoom = StageGraphZoom()

    assert zoom.clamp(100) == zoom.zoom_range[1]
    assert zoom.clamp(-100) == zoom.zoom_range[0]
    assert zoom.clamp(3.5) == 3.5


def test_set_zoom_is_clamped():
    zoom = StageGraphZoom()

    zoom.set_zoom(-100)

    assert zoom.zoom == zoom.zoom_range[0]


def test_step_out_returns_the_inverse_factor():
    zoom = StageGraphZoom()

    factor = zoom.step(zoom_in=False)

    assert factor == pytest.approx(1 / zoom.zoom_in_factor)
    assert zoom.zoom == StageGraphZoom.DEFAULT_ZOOM - zoom.zoom_step


def test_step_past_the_range_is_refused_and_clamped():
    zoom = StageGraphZoom()

    assert zoom.step(zoom_in=True) is None
    assert zoom.zoom == zoom.zoom_range[1]


def test_step_past_the_range_applies_without_clamping():
    zoom = StageGraphZoom()
    zoom.zoom_clamp = False

    assert zoom.step(zoom_in=True) == pytest.approx(zoom.zoom_in_factor)
    assert zoom.zoom == zoom.zoom_range[1]


def test_zoom_to_fit_matches_the_scale_of_the_fit():
    zoom = StageGraphZoom()
    rect = QtCore.QRectF(0, 0, 4000, 1000)

    level = zoom.zoom_to_fit(QtCore.QSize(1000, 1000), rect)

    assert zoom.scale_for(level) == pytest.approx(0.25)


def test_zoom_to_fit_does_not_magnify_past_the_range():
    zoom = StageGraphZoom()

    level = zoom.zoom_to_fit(QtCore.QSize(1000, 1000), QtCore.QRectF(0, 0, 10, 10))

    assert level == zoom.zoom_range[1]


def test_text_antialiasing_only_at_high_zoom():
    zoom = StageGraphZoom()
    assert zoom.wants_text_antialiasing

    zoom.set_zoom(StageGraphZoom.HIGH_QUALITY_ZOOM)

    assert not zoom.wants_text_antialiasing
