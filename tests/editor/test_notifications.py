import threading

import pytest
from PySide6 import QtGui

from nyx.api.v1 import CoreNodes
from nyx.editor.widgets.notifications import NotificationManager


@pytest.fixture
def notification_host(main_window):
    NotificationManager.set_host(main_window)
    main_window.resize(900, 700)
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
