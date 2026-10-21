import pytest
from PySide6 import QtCore

from nyx.api.v1 import CoreNodes
from nyx.editor.graphics.graphics_node_subtitle import GraphicsNodeSubtitle


@pytest.fixture
def make_gr_node(stage_editor, create_node):
    def _make(type_id=CoreNodes.ACTION, name="node"):
        node = create_node(stage_editor.stage, name, type_id=type_id)
        return node, stage_editor.gr_stage.get_gr_node(node)

    return _make


def test_node_without_a_subtitle_shows_none(make_gr_node):
    _node, gr_node = make_gr_node()

    assert not gr_node.subtitle_item.isVisible()
    assert gr_node.subtitle_item.height == 0.0
    assert gr_node.title_height == gr_node.title_item.height


def test_subtitle_is_shown_under_the_title(make_gr_node):
    node, gr_node = make_gr_node()
    plain_height = gr_node.height
    plain_plug_y = gr_node.plugs[0].pos().y()

    node.subtitle = "extra text"

    subtitle = gr_node.subtitle_item
    assert subtitle.isVisible()
    assert subtitle.text() == "extra text"
    assert subtitle.pos().y() > 0
    assert subtitle.pos().y() < gr_node.title_item.height
    assert gr_node.title_height == gr_node.title_item.height + subtitle.height
    # The plugs and the bottom of the node make room for it
    assert gr_node.plugs[0].pos().y() == plain_plug_y + subtitle.height
    assert gr_node.height == plain_height + subtitle.height


def test_subtitle_follows_the_node_without_a_manual_refresh(make_gr_node):
    node, gr_node = make_gr_node()

    node.subtitle = "first"
    assert gr_node.subtitle_item.full_text == "first"

    node.subtitle = "second"
    assert gr_node.subtitle_item.full_text == "second"


def test_clearing_the_subtitle_restores_the_node(make_gr_node):
    node, gr_node = make_gr_node()
    plain_height = gr_node.height
    node.subtitle = "extra text"

    node.subtitle = ""

    assert not gr_node.subtitle_item.isVisible()
    assert gr_node.height == plain_height


def test_long_subtitle_is_elided_and_keeps_both_ends(make_gr_node):
    node, gr_node = make_gr_node()
    long_text = "/stage/" + "very_long_node_name/" * 12 + "end.value"

    node.subtitle = long_text

    subtitle = gr_node.subtitle_item
    assert subtitle.full_text == long_text
    assert "…" in subtitle.text()
    assert subtitle.text().startswith("/stage/")
    # The exact tail kept depends on the platform's font metrics.
    assert subtitle.text().endswith("value")
    assert subtitle.width <= GraphicsNodeSubtitle.MAX_WIDTH + 2.0
    assert subtitle.toolTip() == long_text


def test_short_subtitle_has_no_tooltip(make_gr_node):
    node, gr_node = make_gr_node()

    node.subtitle = "short"

    assert gr_node.subtitle_item.toolTip() == ""


def test_node_grows_to_fit_a_wide_subtitle(make_gr_node):
    node, gr_node = make_gr_node()
    plain_width = gr_node.width

    node.subtitle = "a rather wide subtitle text that needs more room than the title"

    assert gr_node.width > plain_width
    assert gr_node.width >= gr_node.subtitle_item.width + 2 * gr_node.options.subtitle_margin


def test_subtitle_can_not_be_clicked_or_edited(make_gr_node):
    node, gr_node = make_gr_node()
    node.subtitle = "extra text"

    assert gr_node.subtitle_item.acceptedMouseButtons() == QtCore.Qt.MouseButton.NoButton


@pytest.mark.parametrize("type_id", [CoreNodes.GET, CoreNodes.SET])
def test_getter_and_setter_show_the_component_they_point_at(
    make_gr_node, create_node, stage_editor, type_id
):
    create_node(stage_editor.stage, "target", type_id=CoreNodes.LOG)
    node, gr_node = make_gr_node(type_id, "pointer")
    assert not gr_node.subtitle_item.isVisible()

    node["component"].push_value("./target.message")

    assert gr_node.subtitle_item.isVisible()
    assert gr_node.subtitle_item.full_text == "target.message"


def test_subtitle_is_right_aligned(make_gr_node):
    node, gr_node = make_gr_node()

    node.subtitle = "short"

    subtitle = gr_node.subtitle_item
    right_edge = subtitle.pos().x() + subtitle.width
    assert right_edge == gr_node.width - gr_node.options.subtitle_margin


def test_subtitle_stays_right_aligned_when_the_node_grows(make_gr_node):
    node, gr_node = make_gr_node()
    node.subtitle = "short"

    node.subtitle = "a rather wide subtitle text that needs more room than the title"

    subtitle = gr_node.subtitle_item
    assert subtitle.pos().x() + subtitle.width == (
        gr_node.width - gr_node.options.subtitle_margin
    )
    assert subtitle.pos().x() >= gr_node.options.subtitle_margin


def test_title_stays_on_the_left(make_gr_node):
    node, gr_node = make_gr_node()
    node.subtitle = "short"

    assert gr_node.title_item.pos().x() == gr_node.options.title_offset_x
    assert gr_node.subtitle_item.pos().x() > gr_node.title_item.pos().x()
