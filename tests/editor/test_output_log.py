import logging

import pytest
from PySide6 import QtCore, QtWidgets

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


def test_empty_widget_says_ready_and_is_collapsed(log_widget):
    assert log_widget._latest_message_label.toolTip() == "Ready"
    assert not log_widget._latest_severity_indicator_label.isVisibleTo(log_widget)
    assert not log_widget.is_expanded()
    assert not log_widget._log_message_list_view.isVisibleTo(log_widget)


def test_new_record_updates_header(log_widget, log_model):
    log_model.append_log_record(make_record("something broke", logging.ERROR))
    assert log_widget._latest_message_label.toolTip() == "something broke"
    assert log_widget._latest_severity_indicator_label.isVisibleTo(log_widget)


def test_multiline_message_flattened_in_header(log_widget, log_model):
    log_model.append_log_record(make_record("line one\nline two"))
    assert log_widget._latest_message_label.toolTip() == "line one line two"


def test_clearing_model_resets_header(log_widget, log_model):
    log_model.append_log_record(make_record("hello"))
    log_model.clear_log_records()
    assert log_widget._latest_message_label.toolTip() == "Ready"


def test_toggle_expansion_emits_and_shows_history(log_widget, qtbot):
    with qtbot.waitSignal(log_widget.expansion_state_changed) as blocker:
        log_widget.toggle_expanded_state()
    assert blocker.args == [True]
    assert log_widget._log_message_list_view.isVisibleTo(log_widget)

    with qtbot.waitSignal(log_widget.expansion_state_changed) as blocker:
        qtbot.mouseClick(
            log_widget._toggle_expansion_button, QtCore.Qt.MouseButton.LeftButton
        )
    assert blocker.args == [False]
    assert not log_widget._log_message_list_view.isVisibleTo(log_widget)


def test_set_expanded_same_state_does_not_emit(log_widget, qtbot):
    with qtbot.assertNotEmitted(log_widget.expansion_state_changed):
        log_widget.set_expanded(False)


def test_root_logger_records_reach_widget(log_widget, qtbot):
    logging.getLogger("nyx.tests.output_log").warning("via root logger")
    qtbot.waitUntil(
        lambda: log_widget._latest_message_label.toolTip() == "via root logger",
        timeout=2000,
    )


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


# ---- Header ----
def test_header_can_be_hidden(qtbot):
    widget = OutputLogWidget()
    qtbot.addWidget(widget)
    widget.show()
    assert widget._header_widget.isVisible()
    widget.set_header_visible(False)
    assert not widget._header_widget.isVisible()


def _fill(log_model):
    log_model.append_log_record(make_record("alpha debug", logging.DEBUG))
    log_model.append_log_record(make_record("beta info", logging.INFO))
    log_model.append_log_record(make_record("gamma warning", logging.WARNING))
    log_model.append_log_record(make_record("delta error", logging.ERROR))


def test_filter_bar_shown_only_when_expanded(log_widget):
    assert not log_widget._filter_bar.isVisibleTo(log_widget)
    log_widget.set_expanded(True)
    assert log_widget._filter_bar.isVisibleTo(log_widget)


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


def test_filters_do_not_change_header(log_widget, log_model):
    _fill(log_model)
    log_widget._filter_bar.search_text_changed.emit("alpha")
    assert log_widget._latest_message_label.toolTip() == "delta error"


def test_clear_action_empties_model(log_widget, log_model):
    _fill(log_model)
    log_widget._clear_action.trigger()
    assert log_model.rowCount() == 0
    assert log_widget._latest_message_label.toolTip() == "Ready"


def test_filter_bar_settings_menu_clear_empties_model(log_widget, log_model):
    _fill(log_model)
    assert log_widget._filter_bar._settings_button.menu() is not None
    log_widget._filter_bar._clear_log_action.trigger()
    assert log_model.rowCount() == 0


def test_copy_action_copies_selected_records(log_widget, log_model):
    _fill(log_model)
    log_widget.set_expanded(True)
    log_widget._log_message_list_view.selectAll()
    log_widget._copy_action.trigger()
    text = QtWidgets.QApplication.clipboard().text()
    assert text.splitlines() == [
        "alpha debug",
        "beta info",
        "gamma warning",
        "delta error",
    ]
