import pytest
from PySide6 import QtCore, QtGui, QtWidgets

from nyx.api.v1 import CoreNodes, commands
from nyx.core.execution_chain import ExecutionChain
from nyx.core.layered_config import NyxConfig
from nyx.editor.graphics.graphics_link import GraphicsLink
from nyx.editor.graphics.graphics_stage import GraphicsStage
from nyx.static.enums import LinkAnimationStyle
from nyx.editor.graphics.animation.pulse_animation import PulseAnimation


def link(stage, source, target):
    stage.push_command(
        commands.LinkNodeComponentsCommand(stage=stage, source=source, target=target)
    )


@pytest.fixture
def chain(stage_editor, create_node):
    """Flow start -> a -> b, plus a node nobody reaches."""
    stage = stage_editor.stage
    start = create_node(stage, "start", type_id=CoreNodes.FLOW_START)
    a = create_node(stage, "a", type_id=CoreNodes.ACTION)
    b = create_node(stage, "b", type_id=CoreNodes.ACTION)
    loose = create_node(stage, "loose", type_id=CoreNodes.ACTION)
    link(stage, start["flow"], a["flow"])
    link(stage, a["flow"], b["flow"])
    return stage_editor, start, a, b, loose


def pulsing_links(editor):
    return [
        gr_link
        for gr_link in editor.gr_stage.gr_links()
        if gr_link.has_animation(PulseAnimation)
    ]


def pulse_of(gr_link) -> PulseAnimation:
    return gr_link.get_animation(PulseAnimation)


def disable_highlight(monkeypatch):
    monkeypatch.setattr(
        GraphicsStage, "is_flow_chain_highlight_enabled", staticmethod(lambda: False)
    )


# ======== Scene ========= #


def test_flow_links_on_the_chain_pulse(chain):
    editor, *_ = chain
    animator = editor.gr_stage.link_animator

    assert len(editor.gr_stage.gr_links()) == 2
    assert len(pulsing_links(editor)) == 2
    assert animator.links == frozenset(pulsing_links(editor))
    assert animator.is_running


def test_flow_link_off_the_chain_does_not_pulse(stage_editor, create_node):
    stage = stage_editor.stage
    a = create_node(stage, "a", type_id=CoreNodes.ACTION)
    b = create_node(stage, "b", type_id=CoreNodes.ACTION)
    link(stage, a["flow"], b["flow"])  # there is no flow start

    assert len(stage_editor.gr_stage.gr_links()) == 1
    assert pulsing_links(stage_editor) == []
    assert not stage_editor.gr_stage.link_animator.is_running


def test_data_links_never_pulse(chain):
    editor, _start, a, b, _loose = chain  # both nodes are on the chain
    stage = editor.stage
    components = []
    for node in (a, b):
        command = commands.AddNodeComponentCommand(
            node=node, type_id="core:value", name="data"
        )
        stage.push_command(command)
        components.append(command.result_component)
    source, target = components
    source.readable = True
    target.writable = True
    link(stage, source, target)

    data_links = [
        gr_link
        for gr_link in editor.gr_stage.gr_links()
        if gr_link.source_plug.component is source
    ]
    assert len(data_links) == 1
    assert not data_links[0].has_animation(PulseAnimation)
    assert len(pulsing_links(editor)) == 2  # the flow links still do


def test_pulse_follows_links_added_and_removed(chain, create_node):
    editor, start, a, b, loose = chain
    stage = editor.stage
    assert len(pulsing_links(editor)) == 2

    link(stage, b["flow"], loose["flow"])
    assert len(pulsing_links(editor)) == 3

    stage.undo_stack.undo()
    assert len(pulsing_links(editor)) == 2


def test_deleting_the_start_stops_the_pulses(chain):
    editor, start, *_ = chain
    stage = editor.stage

    stage.push_command(commands.DeleteNodeCommand(stage=stage, nodes=[start]))

    assert pulsing_links(editor) == []
    assert not editor.gr_stage.link_animator.is_running


# ======== Config ========= #


def test_highlight_is_on_by_default():
    assert NyxConfig().values.editor_widgets.graphics_stage.highlight_flow_chain is True


@pytest.fixture
def stage_config(main_window):
    """Graphics stage values of the live config, restored after the test."""
    values = main_window.config.values.editor_widgets.graphics_stage
    saved = (values.highlight_flow_chain, values.highlight_flow_chain_style)
    yield values
    values.highlight_flow_chain, values.highlight_flow_chain_style = saved


def test_highlight_style_is_pulse_by_default():
    values = NyxConfig().values.editor_widgets.graphics_stage

    assert values.highlight_flow_chain_style == LinkAnimationStyle.PULSE.value
    assert LinkAnimationStyle.PULSE == "pulse"


def test_the_configured_style_is_used(chain, stage_config):
    editor, *_ = chain
    stage_config.highlight_flow_chain_style = "pulse"

    editor.gr_stage.rebuild_current_scope()

    assert GraphicsStage.get_flow_chain_highlight_style() is LinkAnimationStyle.PULSE
    assert len(pulsing_links(editor)) == 2


def test_an_unknown_style_falls_back_to_the_default(chain, stage_config, caplog):
    editor, *_ = chain
    stage_config.highlight_flow_chain_style = "sparkle"

    with caplog.at_level("WARNING"):
        editor.gr_stage.rebuild_current_scope()

    assert "Unknown flow chain highlight style 'sparkle'" in caplog.text
    assert len(pulsing_links(editor)) == 2


def test_the_highlight_follows_the_live_config(chain, stage_config):
    editor, *_ = chain
    stage_config.highlight_flow_chain = False

    editor.gr_stage.rebuild_current_scope()

    assert pulsing_links(editor) == []

    stage_config.highlight_flow_chain = True
    editor.gr_stage.rebuild_current_scope()

    assert len(pulsing_links(editor)) == 2


def test_disabled_highlight_does_nothing(stage_editor, create_node, monkeypatch):
    disable_highlight(monkeypatch)
    monkeypatch.setattr(
        ExecutionChain,
        "find_node_uuids",
        staticmethod(lambda scope: pytest.fail("the chain was resolved")),
    )
    stage = stage_editor.stage
    start = create_node(stage, "start", type_id=CoreNodes.FLOW_START)
    a = create_node(stage, "a", type_id=CoreNodes.ACTION)
    link(stage, start["flow"], a["flow"])

    assert len(stage_editor.gr_stage.gr_links()) == 1
    assert pulsing_links(stage_editor) == []
    assert not stage_editor.gr_stage.link_animator.is_running


def test_turning_the_highlight_off_clears_the_pulses_on_rebuild(chain, monkeypatch):
    editor, *_ = chain
    assert pulsing_links(editor)

    disable_highlight(monkeypatch)
    editor.gr_stage.rebuild_current_scope()

    assert pulsing_links(editor) == []
    assert editor.gr_stage.link_animator.links == frozenset()
    assert not editor.gr_stage.link_animator.is_running


def test_turning_the_highlight_on_starts_the_pulses_on_rebuild(chain, monkeypatch):
    editor, *_ = chain
    with monkeypatch.context() as patch:
        disable_highlight(patch)
        editor.gr_stage.rebuild_current_scope()
        assert pulsing_links(editor) == []

    editor.gr_stage.rebuild_current_scope()

    assert len(pulsing_links(editor)) == 2


# ======== Dragging ========= #


def test_pulses_pause_while_a_link_is_dragged(chain):
    editor, *_ = chain
    gr_stage = editor.gr_stage
    animator = gr_stage.link_animator
    animator.tick(500)
    assert all(pulse_of(gr_link).offset is not None for gr_link in pulsing_links(editor))

    gr_stage.link_drag_changed.emit(True)
    assert animator.is_paused
    assert not animator.is_running
    assert all(pulse_of(gr_link).offset is None for gr_link in pulsing_links(editor))

    gr_stage.link_drag_changed.emit(False)
    assert not animator.is_paused
    assert animator.is_running


# ======== Painting ========= #


def paint_pulse(gr_link) -> QtGui.QImage:
    rect = gr_link.boundingRect().toAlignedRect()
    image = QtGui.QImage(rect.size(), QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtCore.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(image)
    painter.translate(-rect.topLeft())
    gr_link.get_animation(PulseAnimation).paint_above(painter, gr_link)
    painter.end()
    return image


def paint_link(gr_link) -> QtGui.QImage:
    rect = gr_link.boundingRect().toAlignedRect()
    image = QtGui.QImage(rect.size(), QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtCore.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(image)
    painter.translate(-rect.topLeft())
    gr_link.paint(painter, QtWidgets.QStyleOptionGraphicsItem(), None)
    painter.end()
    return image


def has_pulse_color(image: QtGui.QImage) -> bool:
    pulse = PulseAnimation().color.rgb()
    return any(
        image.pixel(x, y) == pulse
        for x in range(image.width())
        for y in range(image.height())
    )


def has_pulse_pixels(image: QtGui.QImage) -> bool:
    return any(
        image.pixelColor(x, y).alpha() > 0
        for x in range(image.width())
        for y in range(image.height())
    )


def test_pulse_is_drawn_only_for_a_pulsing_link_with_an_offset(chain):
    editor, *_ = chain
    gr_link = pulsing_links(editor)[0]
    assert pulse_of(gr_link).offset is None
    assert not has_pulse_pixels(paint_pulse(gr_link))

    pulse_of(gr_link).offset = 40.0
    assert has_pulse_pixels(paint_pulse(gr_link))

    pulse_of(gr_link).offset = None
    assert not has_pulse_pixels(paint_pulse(gr_link))


def test_pulse_head_is_at_the_offset_along_the_curve(chain):
    editor, *_ = chain
    gr_link = pulsing_links(editor)[0]
    pulse_of(gr_link).offset = 40.0
    path = gr_link.path()
    head = path.pointAtPercent(path.percentAtLength(40.0))
    rect = gr_link.boundingRect().toAlignedRect()

    image = paint_pulse(gr_link)

    pixel = image.pixelColor(round(head.x() - rect.left()), round(head.y() - rect.top()))
    assert pixel.rgb() == PulseAnimation().color.rgb()


def test_pulse_wraps_around_the_length_of_the_link(chain):
    editor, *_ = chain
    gr_link = pulsing_links(editor)[0]
    pulse_of(gr_link).offset = gr_link.path_length * 3 + 40.0
    wrapped = paint_pulse(gr_link)
    pulse_of(gr_link).offset = 40.0

    assert wrapped == paint_pulse(gr_link)


def test_pulse_is_not_drawn_on_a_preview(chain):
    editor, *_ = chain
    plug = pulsing_links(editor)[0].source_plug
    preview = GraphicsLink(source_plug=plug)
    pulse = PulseAnimation()
    pulse.offset = 40.0
    preview.add_animation(pulse)

    assert not has_pulse_color(paint_link(preview))


def test_bounds_leave_room_for_the_pulse(chain):
    editor, *_ = chain
    gr_link = pulsing_links(editor)[0]
    pulsing = gr_link.boundingRect()

    gr_link.remove_animation(PulseAnimation)

    assert (
        pulsing.width() == gr_link.boundingRect().width() + 2 * PulseAnimation().radius
    )


def test_flow_link_of_an_inactive_component_does_not_pulse(stage_editor, create_node):
    stage = stage_editor.stage
    start = create_node(stage, "start", type_id=CoreNodes.FLOW_START)
    branch = create_node(stage, "branch", type_id=CoreNodes.BRANCH)
    on_true = create_node(stage, "on_true", type_id=CoreNodes.ACTION)
    on_false = create_node(stage, "on_false", type_id=CoreNodes.ACTION)
    link(stage, start["flow"], branch["flow"])
    link(stage, branch["true"], on_true["flow"])
    link(stage, branch["false"], on_false["flow"])
    # The condition is true by default: the false output is already inactive.
    assert len(pulsing_links(stage_editor)) == 2

    stage.push_command(
        commands.SetNodeComponentActiveStateCommand(
            stage=stage, node_component=branch["true"], state=False
        )
    )

    pulsing_sources = [
        gr_link.source_plug.component for gr_link in pulsing_links(stage_editor)
    ]
    assert not any(source is branch["true"] for source in pulsing_sources)
    assert len(pulsing_sources) == 1

    stage.undo_stack.undo()
    assert len(pulsing_links(stage_editor)) == 2


def test_pulse_stops_at_an_inactive_node(chain):
    editor, _start, a, b, _loose = chain
    stage = editor.stage
    assert len(pulsing_links(editor)) == 2

    stage.push_command(
        commands.SetNodeActiveStateCommand(stage=stage, node=a, state=False)
    )

    # start -> a still pulses, the link leaving the inactive node does not.
    sources = [gr_link.source_plug.component for gr_link in pulsing_links(editor)]
    assert all(source.node is not a for source in sources)
    assert len(sources) == 1


def test_pulse_of_a_link_scrolled_out_of_the_view_is_not_animated(chain):
    editor, *_ = chain
    animator = editor.gr_stage.link_animator
    gr_links = pulsing_links(editor)
    if not editor.gr_view.isVisible():
        pytest.skip("the view must be shown to have a visible area")
    assert animator.is_animating

    for gr_node in editor.gr_stage.gr_nodes():
        gr_node.setPos(100000, 100000)

    assert animator.is_running
    assert animator.active_links() == []
    assert not animator.is_animating
    for gr_link in gr_links:
        assert gr_link not in animator.active_links()
