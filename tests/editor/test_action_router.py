import pytest
from PySide6 import QtCore, QtWidgets
from unittest import mock

from nyx.core.exceptions import ActionLookupError
from nyx.editor.core.action_registry import ActionRegistry
from nyx.editor.core.action_router import ActionRouter
from nyx.editor.core.actions import ActionId, register_default_actions


@pytest.fixture
def registry(qtbot) -> ActionRegistry:
    registry = ActionRegistry()
    register_default_actions(registry)
    return registry


@pytest.fixture
def router(registry) -> ActionRouter:
    return ActionRouter(registry)


@pytest.fixture
def focus_pair(qtbot):
    """Window with two sibling focusable line edits inside separate containers."""
    window = QtWidgets.QWidget()
    layout = QtWidgets.QHBoxLayout(window)
    left_box, right_box = QtWidgets.QWidget(), QtWidgets.QWidget()
    left, right = QtWidgets.QLineEdit(), QtWidgets.QLineEdit()
    for box, edit in ((left_box, left), (right_box, right)):
        QtWidgets.QVBoxLayout(box).addWidget(edit)
        layout.addWidget(box)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    return window, left_box, left, right_box, right


def _focus(qtbot, widget: QtWidgets.QWidget):
    widget.window().activateWindow()
    widget.setFocus()
    qtbot.waitUntil(widget.hasFocus, timeout=2000)


def test_shortcut_triggers_handler(registry, router, qtbot):
    window = QtWidgets.QWidget()
    qtbot.addWidget(window)
    calls = []
    router.register_handler(ActionId.SAVE_STAGE, lambda: calls.append(1))
    registry.attach_shortcuts(window)
    window.show()
    qtbot.waitExposed(window)
    window.activateWindow()
    qtbot.waitUntil(window.isActiveWindow, timeout=2000)

    qtbot.keyClick(
        window,
        QtCore.Qt.Key.Key_S,
        QtCore.Qt.KeyboardModifier.ControlModifier
        | QtCore.Qt.KeyboardModifier.ShiftModifier,
    )
    assert calls == [1]


# ---- Handler resolution ----
def test_scoped_handler_beats_global(registry, router, qtbot):
    calls = []
    outer = QtWidgets.QWidget()
    qtbot.addWidget(outer)
    inner = QtWidgets.QWidget(outer)
    child = QtWidgets.QWidget(inner)
    other = QtWidgets.QWidget()
    qtbot.addWidget(other)
    router.register_handler(ActionId.COPY, lambda: calls.append("global"))
    router.register_handler(ActionId.COPY, lambda: calls.append("inner"), scope=inner)

    router.resolve_handler(ActionId.COPY, child)()
    router.resolve_handler(ActionId.COPY, other)()
    assert calls == ["inner", "global"]


def test_nearest_scope_wins(registry, router, qtbot):
    calls = []
    outer = QtWidgets.QWidget()
    qtbot.addWidget(outer)
    inner = QtWidgets.QWidget(outer)
    router.register_handler(ActionId.COPY, lambda: calls.append("outer"), scope=outer)
    router.register_handler(ActionId.COPY, lambda: calls.append("inner"), scope=inner)
    router.resolve_handler(ActionId.COPY, inner)()
    assert calls == ["inner"]


def test_no_handler_without_global_returns_none(registry, router, qtbot):
    scoped = QtWidgets.QWidget()
    qtbot.addWidget(scoped)
    other = QtWidgets.QWidget()
    qtbot.addWidget(other)
    router.register_handler(ActionId.COPY, lambda: None, scope=scoped)
    assert router.resolve_handler(ActionId.COPY, other) is None


def test_dispatch_without_handler_warns(registry, router, caplog):
    with caplog.at_level("WARNING"):
        assert router.dispatch(ActionId.COPY) is False
    assert "No handler" in caplog.text


def test_unregister_handler(registry, router):
    action = registry.action(ActionId.COPY)
    handle = router.register_handler(ActionId.COPY, lambda: None)
    assert action.isEnabled()
    router.unregister_handler(handle)
    assert not action.isEnabled()
    router.unregister_handler(handle)  # unknown handle is a no-op


def test_bound_method_handler_is_weak(registry, router):
    class Target:
        def run(self):
            pass

    target = Target()
    router.register_handler(ActionId.COPY, target.run)
    assert router.resolve_handler(ActionId.COPY) is not None
    del target  # no cycle: refcounting frees it immediately
    assert router.resolve_handler(ActionId.COPY) is None


def test_handler_dropped_when_scope_destroyed(registry, router, qtbot):
    widget = QtWidgets.QWidget()
    router.register_handler(ActionId.COPY, lambda: None, scope=widget)
    assert router.resolve_binding(ActionId.COPY, widget) is not None
    widget.deleteLater()
    qtbot.waitUntil(lambda: router.resolve_binding(ActionId.COPY) is None)


# ---- Triggering and enabled state ----
def test_triggering_shared_action_dispatches(registry, router):
    calls = []
    router.register_handler(ActionId.COPY, lambda: calls.append(1))
    registry.action(ActionId.COPY).trigger()
    assert calls == [1]


def test_no_handler_disables_action(registry, router):
    action = registry.action(ActionId.COPY)
    assert not action.isEnabled()
    router.register_handler(ActionId.COPY, lambda: None)
    assert action.isEnabled()


def test_condition_controls_enabled_state(registry, router):
    state = {"on": False}
    router.register_handler(ActionId.CUT, lambda: None, condition=lambda: state["on"])
    action = registry.action(ActionId.CUT)
    assert not action.isEnabled()
    state["on"] = True
    router.refresh_enabled(ActionId.CUT)
    assert action.isEnabled()


def test_focus_change_switches_handler_and_enabled(registry, router, qtbot, focus_pair):
    _window, left_box, left, right_box, right = focus_pair
    calls = []
    router.register_handler(ActionId.COPY, lambda: calls.append("left"), scope=left_box)
    router.register_handler(
        ActionId.COPY, lambda: calls.append("right"), scope=right_box
    )
    action = registry.action(ActionId.COPY)

    _focus(qtbot, left)
    qtbot.waitUntil(action.isEnabled, timeout=2000)
    action.trigger()
    _focus(qtbot, right)
    action.trigger()
    assert calls == ["left", "right"]


def test_action_disabled_when_focus_leaves_all_scopes(
    registry, router, qtbot, focus_pair
):
    _window, left_box, left, _right_box, right = focus_pair
    router.register_handler(ActionId.COPY, lambda: None, scope=left_box)
    action = registry.action(ActionId.COPY)

    _focus(qtbot, left)
    qtbot.waitUntil(action.isEnabled, timeout=2000)
    _focus(qtbot, right)
    qtbot.waitUntil(lambda: not action.isEnabled(), timeout=2000)


def test_register_handler_unknown_action_raises(router):
    with pytest.raises(ActionLookupError):
        router.register_handler("nope", lambda: None)


def test_action_created_after_handler_registered_is_enabled(registry, router):
    router.register_handler(ActionId.COPY, lambda: None)
    assert registry.action(ActionId.COPY).isEnabled()


def test_condition_respected_for_late_created_action(registry, router):
    router.register_handler(ActionId.COPY, lambda: None, condition=lambda: False)
    assert not registry.action(ActionId.COPY).isEnabled()


def test_router_wires_actions_that_already_exist(registry):
    action = registry.action(ActionId.COPY)
    calls = []
    router = ActionRouter(registry)
    router.register_handler(ActionId.COPY, lambda: calls.append(1))
    assert action.isEnabled()
    action.trigger()
    assert calls == [1]


def test_registry_clear_drops_handlers(registry, router):
    router.register_handler(ActionId.COPY, lambda: None)
    registry.clear()
    assert router.resolve_handler(ActionId.COPY) is None


# ---- Editor wiring ----
def test_tree_view_create_node_opens_centered_palette():
    from nyx.editor.views.stage_tree_view import StageTreeView

    view = mock.Mock()
    StageTreeView.create_new_node(view)
    view.current_stage_graph.show_nodes_palette_centered.assert_called_once_with()


def test_tree_view_create_node_without_stage_graph_is_noop():
    from nyx.editor.views.stage_tree_view import StageTreeView

    view = mock.Mock(current_stage_graph=None)
    StageTreeView.create_new_node(view)  # must not raise


def test_graph_view_create_node_passes_mouse_position():
    from nyx.editor.views.stage_graph_view import StageGraphView

    view = mock.Mock()
    StageGraphView.create_new_node(view)
    view.graph_editor.show_nodes_palette_centered.assert_called_once_with(
        view.last_scene_mouse_pos
    )


def test_main_window_show_nodes_palette_delegates_to_current_graph():
    from nyx.editor.main_window import NyxEditorMainWindow

    window = mock.Mock()
    NyxEditorMainWindow.show_nodes_palette(window)
    window.current_stage_graph.show_nodes_palette_centered.assert_called_once_with()

    window = mock.Mock(current_stage_graph=None)
    NyxEditorMainWindow.show_nodes_palette(window)  # must not raise


def test_action_condition_changed_refreshes_action(registry, router):
    from nyx.editor.core.action_condition import CallableCondition

    state = {"on": False}
    condition = CallableCondition(lambda: state["on"])
    router.register_handler(ActionId.CUT, lambda: None, condition=condition)
    action = registry.action(ActionId.CUT)
    assert not action.isEnabled()

    state["on"] = True
    condition.notify()  # no manual refresh
    assert action.isEnabled()


def test_unregistered_condition_no_longer_refreshes_action(registry, router):
    from nyx.editor.core.action_condition import CallableCondition

    state = {"on": False}
    condition = CallableCondition(lambda: state["on"])
    handle = router.register_handler(ActionId.CUT, lambda: None, condition=condition)
    router.unregister_handler(handle)
    router.register_handler(ActionId.CUT, lambda: None)
    action = registry.action(ActionId.CUT)
    assert action.isEnabled()

    state["on"] = False
    with mock.patch.object(router, "refresh_enabled") as refresh:
        condition.notify()
    refresh.assert_not_called()


def test_conditions_combine_and_relay_changes(qtbot):
    from nyx.editor.core.action_condition import CallableCondition

    flags = {"a": True, "b": True}
    a = CallableCondition(lambda: flags["a"], description="a")
    b = CallableCondition(lambda: flags["b"], description="b")
    both, either, not_a = a & b, a | b, ~a
    assert both() and either() and not not_a()
    assert both.description == "(a and b)"
    assert not_a.description == "not a"

    flags["a"] = False
    assert not both() and either() and not_a()
    flags["b"] = False
    assert not either()

    with qtbot.waitSignal(both.changed, timeout=500):
        a.notify()
    with qtbot.waitSignal(not_a.changed, timeout=500):
        a.notify()


def test_plain_callable_combines_with_condition():
    from nyx.editor.core.action_condition import CallableCondition

    condition = CallableCondition(lambda: True) & (lambda: False)
    assert not condition()
    assert ((lambda: True) & CallableCondition(lambda: True))()
    assert not ((lambda: False) | CallableCondition(lambda: False))()
