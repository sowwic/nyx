import math

import pytest
from PySide6 import QtCore, QtGui

from tests.editor.paint_helpers import render_link

from nyx.api.v1 import CoreNodes, commands
from nyx.editor.graphics import link_path
from nyx.editor.graphics.animation.pulse_animation import PulseAnimation
from nyx.editor.graphics.graphics_link import GraphicsLink
from nyx.editor.graphics.link_path import (
    MIN_TANGENT,
    PATH_BUILDERS,
    SQUARE_HANDLE_WEIGHT,
    build_bezier_path,
    build_direct_path,
    build_link_path,
    build_square_path,
    get_link_style,
)
from nyx.static.enums import LinkStyle

START = QtCore.QPointF(10.0, 20.0)
END = QtCore.QPointF(410.0, 220.0)


def points(path: QtGui.QPainterPath) -> list[tuple[float, float]]:
    return [
        (path.elementAt(i).x, path.elementAt(i).y) for i in range(path.elementCount())
    ]


# ======== Builders ========= #


def test_every_style_has_a_builder():
    assert set(PATH_BUILDERS) == set(LinkStyle)


@pytest.mark.parametrize("style", list(LinkStyle))
@pytest.mark.parametrize(
    "start, end",
    [
        (START, END),
        (END, START),  # the target is behind the source
        (START, QtCore.QPointF(START)),  # on top of each other
    ],
)
def test_every_style_runs_from_the_start_to_the_end(style, start, end):
    path = build_link_path(style, start, end)

    assert path.pointAtPercent(0.0) == start
    assert path.pointAtPercent(1.0) == end


def test_bezier_leaves_to_the_right_and_enters_from_the_left():
    path = build_bezier_path(START, END)

    move, control1, control2, target = points(path)
    tangent = (END.x() - START.x()) * 0.5
    assert move == (START.x(), START.y())
    assert control1 == (START.x() + tangent, START.y())
    assert control2 == (END.x() - tangent, END.y())
    assert target == (END.x(), END.y())


def test_bezier_between_close_plugs_keeps_the_minimum_handle():
    end = QtCore.QPointF(START.x() + 10.0, START.y() + 50.0)

    _move, control1, control2, _target = points(build_bezier_path(START, end))

    assert control1[0] == START.x() + MIN_TANGENT
    assert control2[0] == end.x() - MIN_TANGENT


def test_direct_is_a_straight_line():
    path = build_direct_path(START, END)

    assert points(path) == [(START.x(), START.y()), (END.x(), END.y())]
    assert path.length() == pytest.approx(
        math.dist((START.x(), START.y()), (END.x(), END.y()))
    )


def test_square_turns_at_right_angles_half_way():
    path = build_square_path(START, END)

    mid_x = START.x() + (END.x() - START.x()) * SQUARE_HANDLE_WEIGHT
    assert points(path) == [
        (START.x(), START.y()),
        (mid_x, START.y()),
        (mid_x, END.y()),
        (END.x(), END.y()),
    ]


# ======== Config ========= #


def test_link_style_is_bezier_by_default():
    from nyx.core.config_values.graphics_values import NyxEditorGraphicsStageConfigValues

    assert NyxEditorGraphicsStageConfigValues().link_style == LinkStyle.BEZIER.value


@pytest.mark.parametrize("style", list(LinkStyle))
def test_the_configured_style_is_read(stage_config, style):
    stage_config.link_style = style.value

    assert get_link_style() is style


def test_an_unknown_style_falls_back_once(stage_config, caplog, monkeypatch):
    monkeypatch.setattr(link_path, "_warned_styles", set())
    stage_config.link_style = "wavy"

    with caplog.at_level("WARNING"):
        first = get_link_style()
        second = get_link_style()

    assert first is second is LinkStyle.BEZIER
    assert caplog.text.count("Unknown link style 'wavy'") == 1


# ======== Link ========= #


@pytest.fixture
def two_nodes(stage_editor, create_node):
    stage = stage_editor.stage
    start = create_node(stage, "start", type_id=CoreNodes.FLOW_START)
    action = create_node(stage, "action", type_id=CoreNodes.ACTION)
    # Positions come from the model, the scope is rebuilt from it when linking.
    stage.push_command(
        commands.MoveNodeCommand(
            stage=stage,
            nodes=[start, action],
            new_positions=[QtCore.QPointF(0, 0), QtCore.QPointF(400, 150)],
        )
    )
    return stage_editor, stage, start, action


def make_link(two_nodes) -> GraphicsLink:
    editor, stage, start, action = two_nodes
    stage.push_command(
        commands.LinkNodeComponentsCommand(
            stage=stage, source=start["flow"], target=action["flow"]
        )
    )
    return editor.gr_stage.gr_links()[0]


def test_new_link_uses_the_configured_style(two_nodes, stage_config):
    stage_config.link_style = "square"

    gr_link = make_link(two_nodes)

    assert gr_link.style is LinkStyle.SQUARE
    assert gr_link.path().elementCount() == 4


def test_a_link_can_be_given_a_style(two_nodes):
    editor, _stage, start, action = two_nodes
    source = editor.gr_stage.get_gr_node(start).get_plug(start["flow"])
    target = editor.gr_stage.get_gr_node(action).get_plug(action["flow"])

    gr_link = GraphicsLink(source, target, style=LinkStyle.DIRECT)

    assert gr_link.style is LinkStyle.DIRECT
    assert gr_link.path().elementCount() == 2


def test_changing_the_style_rebuilds_the_path(two_nodes, stage_config):
    stage_config.link_style = "bezier"
    gr_link = make_link(two_nodes)
    start, end = gr_link.path().pointAtPercent(0.0), gr_link.path().pointAtPercent(1.0)
    bezier_length = gr_link.path_length

    gr_link.set_style(LinkStyle.DIRECT)

    assert gr_link.style is LinkStyle.DIRECT
    assert gr_link.path().pointAtPercent(0.0) == start
    assert gr_link.path().pointAtPercent(1.0) == end
    assert gr_link.path_length == pytest.approx(
        math.dist((start.x(), start.y()), (end.x(), end.y()))
    )
    assert gr_link.path_length < bezier_length


def test_setting_the_same_style_keeps_the_path(two_nodes, stage_config):
    stage_config.link_style = "square"
    gr_link = make_link(two_nodes)
    path = gr_link.path()

    gr_link.set_style(LinkStyle.SQUARE)

    assert gr_link.path() == path


def test_link_follows_its_plugs_in_every_style(two_nodes, stage_config):
    editor, _stage, _start, action = two_nodes
    stage_config.link_style = "square"
    gr_link = make_link(two_nodes)
    before = gr_link.path().pointAtPercent(1.0)

    editor.gr_stage.get_gr_node(action).setPos(600, 300)

    after = gr_link.path().pointAtPercent(1.0)
    assert after.x() == pytest.approx(before.x() + 200)
    assert after.y() == pytest.approx(before.y() + 150)
    assert gr_link.path().elementCount() == 4


def test_rebuilding_the_scope_applies_a_new_style(two_nodes, stage_config):
    stage_config.link_style = "bezier"
    gr_link = make_link(two_nodes)
    assert gr_link.style is LinkStyle.BEZIER

    stage_config.link_style = "direct"
    two_nodes[0].gr_stage.rebuild_current_scope()

    assert two_nodes[0].gr_stage.gr_links()[0].style is LinkStyle.DIRECT


def test_corners_of_square_links_are_rounded(two_nodes, stage_config):
    stage_config.link_style = "square"
    gr_link = make_link(two_nodes)

    assert gr_link.pen().joinStyle() == QtCore.Qt.PenJoinStyle.RoundJoin


def test_preview_uses_the_configured_style(two_nodes, stage_config):
    editor, _stage, start, _action = two_nodes
    stage_config.link_style = "square"
    plug = editor.gr_stage.get_gr_node(start).get_plug(start["flow"])

    preview = GraphicsLink(source_plug=plug)
    preview.set_floating_pos(QtCore.QPointF(300, 100))

    assert preview.style is LinkStyle.SQUARE
    assert preview.path().elementCount() == 4


def test_animations_follow_a_path_that_is_not_a_curve(two_nodes, stage_config):
    stage_config.link_style = LinkStyle.SQUARE.value
    gr_link = make_link(two_nodes)
    two_nodes[0].gr_stage.link_animator.clear()
    pulse = PulseAnimation()
    pulse.offset = gr_link.path_length * 0.5
    gr_link.add_animation(pulse)

    image = render_link(gr_link, lambda painter: pulse.paint_above(painter, gr_link))

    path = gr_link.path()
    head = path.pointAtPercent(path.percentAtLength(pulse.offset))
    spot = head - gr_link.boundingRect().toAlignedRect().topLeft().toPointF()
    assert image.pixelColor(round(spot.x()), round(spot.y())).rgb() == pulse.color.rgb()
