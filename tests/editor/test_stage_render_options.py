from PySide6 import QtGui

from nyx.static.enums import StageBackGroundStyle


def _render(gr_stage) -> QtGui.QImage:
    image = QtGui.QImage(200, 200, QtGui.QImage.Format.Format_ARGB32)
    painter = QtGui.QPainter(image)
    gr_stage.render(painter)
    painter.end()
    return image


def test_defaults(stage_editor, stage_config):
    gr_stage = stage_editor.gr_stage
    assert gr_stage.get_background_style() == StageBackGroundStyle.GRID
    assert gr_stage.options.grid_size == 20


def test_background_color_from_config(stage_editor, stage_config):
    gr_stage = stage_editor.gr_stage
    stage_config.background_color = "#101010"
    gr_stage.apply_render_options()
    assert gr_stage.backgroundBrush().color() == QtGui.QColor("#101010")


def test_invalid_values_fall_back(stage_editor, stage_config):
    gr_stage = stage_editor.gr_stage
    stage_config.background_style = "bogus"
    stage_config.background_color = "not a color"
    gr_stage.apply_render_options()
    assert gr_stage.get_background_style() == StageBackGroundStyle.GRID
    assert gr_stage.backgroundBrush().color().isValid()


def test_styles_draw(stage_editor, stage_config):
    gr_stage = stage_editor.gr_stage
    for style in StageBackGroundStyle:
        stage_config.background_style = style.value
        gr_stage.apply_render_options()
        assert not _render(gr_stage).isNull()
