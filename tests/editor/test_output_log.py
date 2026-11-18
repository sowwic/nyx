import logging

import pytest
from PySide6 import QtWidgets

from nyx.core.models.log_record_model import LogRecordListModel
from nyx.editor.widgets.output_log.output_log_widget import OutputLogWidget


def make_record(message: str, level: int = logging.INFO) -> logging.LogRecord:
    return logging.LogRecord("test", level, __file__, 1, message, None, None)


@pytest.fixture
def log_model():
    return LogRecordListModel()


@pytest.fixture
def log_widget(qtbot, log_model):
    widget = OutputLogWidget(log_message_list_model=log_model)
    qtbot.addWidget(widget)
    widget.resize(400, 200)
    widget.show()
    return widget


def test_filter_bar_and_list_are_always_shown(log_widget):
    assert log_widget._filter_bar.isVisibleTo(log_widget)
    assert log_widget._log_message_list_view.isVisibleTo(log_widget)


def test_root_logger_records_reach_widget(log_widget, log_model, qtbot):
    logging.getLogger("nyx.tests.output_log").warning("via root logger")
    qtbot.waitUntil(
        lambda: (
            log_model.latest_log_record() is not None
            and log_model.latest_log_record().getMessage() == "via root logger"
        ),
        timeout=2000,
    )


def _scroll_bar(log_widget):
    return log_widget._log_message_list_view.verticalScrollBar()


def test_new_records_scroll_the_list_to_the_newest(log_widget, log_model, qtbot):
    for number in range(200):
        log_model.append_log_record(make_record(f"record {number}"))

    qtbot.waitUntil(
        lambda: _scroll_bar(log_widget).value() == _scroll_bar(log_widget).maximum(),
        timeout=2000,
    )
    assert _scroll_bar(log_widget).maximum() > 0


def test_records_that_came_while_hidden_are_scrolled_to_when_shown(
    log_widget, log_model, qtbot
):
    log_widget.hide()
    for number in range(200):
        log_model.append_log_record(make_record(f"record {number}"))

    log_widget.show()

    qtbot.waitUntil(
        lambda: _scroll_bar(log_widget).value() == _scroll_bar(log_widget).maximum(),
        timeout=2000,
    )
    assert _scroll_bar(log_widget).maximum() > 0


def test_message_of_a_record_with_a_dead_argument_falls_back_to_the_raw_message():
    class Dead:
        def __repr__(self):
            raise RuntimeError("already deleted")

    record = logging.LogRecord(
        "test", logging.INFO, __file__, 1, "gone %r", (Dead(),), None
    )
    model = LogRecordListModel()
    model.append_log_record(record)
    assert model.index(0).data() == "gone %r"


def test_log_model_trims_to_maximum():
    model = LogRecordListModel(maximum_retained_log_record_count=3)
    for number in range(5):
        model.append_log_record(make_record(str(number)))
    assert model.rowCount() == 3
    assert model.latest_log_record().getMessage() == "4"
    assert model.index(0).data() == "2"


def _fill(log_model):
    log_model.append_log_record(make_record("alpha debug", logging.DEBUG))
    log_model.append_log_record(make_record("beta info", logging.INFO))
    log_model.append_log_record(make_record("gamma warning", logging.WARNING))
    log_model.append_log_record(make_record("delta error", logging.ERROR))


def test_search_text_filters_rows(log_widget, log_model):
    _fill(log_model)
    log_widget._filter_bar.search_text_changed.emit("GAMMA")
    assert log_widget._filter_model.rowCount() == 1
    log_widget._filter_bar.search_text_changed.emit("")
    assert log_widget._filter_model.rowCount() == 4


def test_minimum_level_filters_rows(log_widget, log_model):
    _fill(log_model)
    log_widget._filter_bar._level_combo_box.setCurrentIndex(2)
    assert log_widget._filter_model.rowCount() == 2
    log_widget._filter_bar._level_combo_box.setCurrentIndex(0)
    assert log_widget._filter_model.rowCount() == 4


def test_clear_action_empties_model(log_widget, log_model):
    _fill(log_model)
    log_widget._clear_action.trigger()
    assert log_model.rowCount() == 0


def test_filter_bar_settings_menu_clear_empties_model(log_widget, log_model):
    _fill(log_model)
    assert log_widget._filter_bar._settings_button.menu() is not None
    log_widget._filter_bar._clear_log_action.trigger()
    assert log_model.rowCount() == 0


def test_copy_action_copies_selected_records(log_widget, log_model):
    _fill(log_model)
    log_widget._log_message_list_view.selectAll()
    log_widget._copy_action.trigger()
    text = QtWidgets.QApplication.clipboard().text()
    assert text.splitlines() == [
        "alpha debug",
        "beta info",
        "gamma warning",
        "delta error",
    ]
