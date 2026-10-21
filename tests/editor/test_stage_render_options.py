from PySide6 import QtGui

from nyx.static.enums import LinkStyle, StageBackGroundStyle


def _render(gr_stage) -> QtGui.QImage:
    image = QtGui.QImage(200, 200, QtGui.QImage.Format.Format_ARGB32)
    painter = QtGui.QPainter(image)
    gr_stage.render(painter)
    painter.end()
    return image


def test_defaults(stage_editor, stage_config):
    gr_stage = stage_editor.gr_stage
    default = type(stage_config).model_fields["background_style"].default
    assert gr_stage.get_background_style() == StageBackGroundStyle(default)
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


def test_reset_config_reapplies(main_window, stage_editor, stage_config, qtbot):
    gr_stage = stage_editor.gr_stage
    stage_config.background_color = "#101010"
    gr_stage.apply_render_options()
    main_window.reset_application_config()
    default = QtGui.QColor(type(stage_config).model_fields["background_color"].default)
    qtbot.waitUntil(lambda: gr_stage.backgroundBrush().color() == default, timeout=2000)


def test_reset_config_reapplies_link_style(main_window, chain_link, stage_config, qtbot):
    editor, _ = chain_link
    stage_config.link_style = LinkStyle.DIRECT.value
    editor.gr_stage.rebuild_current_scope()
    assert editor.gr_stage.gr_links()[0].style == LinkStyle.DIRECT
    main_window.reset_application_config()
    qtbot.waitUntil(
        lambda: editor.gr_stage.gr_links()[0].style == LinkStyle.BEZIER, timeout=2000
    )
