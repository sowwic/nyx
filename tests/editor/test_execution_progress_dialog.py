import logging
import time

from PySide6 import QtWidgets

from nyx.api.v1 import Stage
from nyx.editor.widgets.dialogs.execution_progress_dialog import (
    ExecutionProgressDialog,
)


def make_record(message, level=logging.INFO):
    return logging.LogRecord("test", level, __file__, 1, message, None, None)


def test_the_label_follows_info_records_and_ignores_debug(qapp):
    crawler = Stage().crawler
    dialog = ExecutionProgressDialog(crawler)

    dialog.on_record_logged(make_record("first"))
    dialog.on_record_logged(make_record("noise", logging.DEBUG))
    assert dialog.message == "first"

    dialog.on_record_logged(make_record("multi\nline"))
    assert dialog.message == "multi line"


def test_cancel_requests_it_and_disables_the_button(qapp):
    crawler = Stage().crawler
    dialog = ExecutionProgressDialog(crawler)

    dialog.cancel()

    assert crawler.is_cancel_requested
    assert dialog.message == "Cancelling..."
    dialog.on_record_logged(make_record("late"))
    assert dialog.message == "Cancelling..."


def test_escape_cancels_instead_of_closing(qapp):
    crawler = Stage().crawler
    dialog = ExecutionProgressDialog(crawler)

    dialog.reject()

    assert crawler.is_cancel_requested


def test_it_shows_only_after_the_delay_and_hides_afterwards(qapp):
    crawler = Stage().crawler
    dialog = ExecutionProgressDialog(crawler)
    dialog.SHOW_DELAY_MS = 100
    dialog._show_timer.setInterval(100)

    with dialog.watching():
        assert not dialog.isVisible()
        deadline = time.monotonic() + 2
        while not dialog.isVisible() and time.monotonic() < deadline:
            QtWidgets.QApplication.processEvents()
            time.sleep(0.01)
        assert dialog.isVisible()
        assert crawler.accept_user_input
        logging.getLogger("tests.dialog").warning("hello from the log")
        QtWidgets.QApplication.processEvents()
        assert dialog.message == "hello from the log"

    assert not dialog.isVisible()


def test_a_quick_run_never_shows_it(qapp):
    crawler = Stage().crawler
    dialog = ExecutionProgressDialog(crawler)

    with dialog.watching():
        QtWidgets.QApplication.processEvents()

    assert not dialog.isVisible()
    assert not dialog._show_timer.isActive()
