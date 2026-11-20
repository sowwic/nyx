import threading

import pytest
from PySide6 import QtGui

from nyx.api.v1 import CoreNodes
from nyx.editor.widgets.notifications import NotificationManager
from nyx.editor.panels.panel_definitions import PanelId


@pytest.fixture
def notification_host(main_window):
    NotificationManager.set_host(main_window)
    main_window.resize(900, 700)
    yield main_window
    NotificationManager.set_host(None)


@pytest.fixture
def floating_notification_host(main_window, manager):
    """The window with messages floating in the top right corner, as in the editor."""
    NotificationManager.set_host(main_window, main_window.panel_host)
    main_window.resize(900, 700)
    main_window.show()
    yield main_window
    NotificationManager.set_host(None)


def test_without_a_host_messages_are_ignored(qapp):
    NotificationManager.set_host(None)

    assert NotificationManager.add_message("hi") is None


def test_a_message_is_a_child_of_the_host_in_its_bottom_right_corner(notification_host):
    message = NotificationManager.add_message("hello", fade=5)

    assert message.parent() is notification_host
    assert message.text == "hello"
    assert message.geometry().right() < notification_host.width()
    assert message.geometry().bottom() < notification_host.height()
    assert (
        notification_host.width() - message.geometry().right()
        <= NotificationManager.MARGIN + 1
    )


def test_messages_stack_upwards_newest_at_the_bottom(notification_host):
    first = NotificationManager.add_message("one")
    second = NotificationManager.add_message("two")

    assert second.y() > first.y()
    assert second.geometry().bottom() < notification_host.height()


def test_the_x_dismisses_it_early_and_the_gap_closes(notification_host, qtbot):
    first = NotificationManager.add_message("one", fade=60)
    second = NotificationManager.add_message("two", fade=60)
    old_y = first.y()
    second.dismiss_button.click()

    qtbot.waitUntil(
        lambda: NotificationManager._instance.messages == [first], timeout=3000
    )

    assert first.y() > old_y


def test_it_fades_out_after_its_time_and_without_one_it_stays(notification_host, qtbot):
    NotificationManager.add_message("timed", fade=0.1)
    kept = NotificationManager.add_message("kept")

    qtbot.waitUntil(
        lambda: NotificationManager._instance.messages == [kept], timeout=3000
    )

    assert not kept.is_closing


def test_messages_follow_the_corner_when_the_window_is_resized(notification_host):
    message = NotificationManager.add_message("hi")
    notification_host.resize(1200, 900)

    assert (
        notification_host.width() - message.geometry().right()
        <= NotificationManager.MARGIN + 1
    )
    assert (
        notification_host.height() - message.geometry().bottom()
        <= NotificationManager.MARGIN + 1
    )


def test_a_worker_thread_can_add_a_message(notification_host, qtbot):
    thread = threading.Thread(target=lambda: NotificationManager.add_message("later"))
    thread.start()
    thread.join()

    qtbot.waitUntil(
        lambda: len(NotificationManager._instance.messages) == 1, timeout=3000
    )


def test_an_icon_from_the_resources_is_shown(notification_host):
    message = NotificationManager.add_message("ok", icon=":/icons/green_check")

    assert not message._icon_label.pixmap().isNull()
    assert isinstance(message._icon_label.pixmap(), QtGui.QPixmap)


def test_executing_a_stage_says_whether_it_succeeded(
    notification_host, stage_editor, create_node
):
    create_node(stage_editor.stage, "a", type_id=CoreNodes.FLOW_START)

    notification_host.execute_stage_graph()

    assert [m.text for m in NotificationManager._instance.messages] == [
        "Execution succeeded"
    ]


def test_a_failing_stage_gives_one_failure_message(
    notification_host, stage_editor, create_node
):
    node = create_node(stage_editor.stage, "a", type_id=CoreNodes.FLOW_START)
    node.execute = lambda: (_ for _ in ()).throw(ValueError("boom"))

    with pytest.raises(ValueError):
        notification_host.execute_stage_graph()

    assert [m.text for m in NotificationManager._instance.messages] == [
        "Execution failed"
    ]


def test_floating_messages_stack_under_the_stage_controls_overlay(
    floating_notification_host,
):
    window = floating_notification_host
    host = window.panel_host
    overlay = window.stage_controls_overlay

    first = NotificationManager.add_message("one")
    second = NotificationManager.add_message("two")

    assert first.parent() is host.canvas
    assert first.y() == overlay.geometry().bottom() + 1 + host.FLOATING_SPACING
    assert second.y() == first.geometry().bottom() + 1 + host.FLOATING_SPACING
    assert first.geometry().right() == overlay.geometry().right()


def test_dismissing_a_floating_message_closes_the_gap(floating_notification_host, qtbot):
    first = NotificationManager.add_message("one", fade=60)
    second = NotificationManager.add_message("two", fade=60)
    first_y = first.y()

    first.dismiss_button.click()

    qtbot.waitUntil(
        lambda: NotificationManager._instance.messages == [second], timeout=3000
    )
    assert second.y() == first_y


def test_floating_messages_move_aside_for_the_right_panel(
    floating_notification_host, qtbot
):
    window = floating_notification_host
    message = NotificationManager.add_message("hi")
    closed_right = message.geometry().right()

    window.panel_manager.set_open(PanelId.INSPECTOR, True)
    inspector = window.panel_manager.panel(PanelId.INSPECTOR)
    try:
        assert message.geometry().right() < inspector.x()
        assert message.geometry().right() < closed_right
    finally:
        window.panel_manager.set_open(PanelId.INSPECTOR, False)


def test_replacing_the_host_removes_the_messages(floating_notification_host):
    host = floating_notification_host.panel_host
    message = NotificationManager.add_message("stays", fade=60)
    assert any(widget is message for widget, _ in host._floating)

    NotificationManager.set_host(None)

    assert not any(widget is message for widget, _ in host._floating)
