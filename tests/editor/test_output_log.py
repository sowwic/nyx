import logging
import types

import pytest
from PySide6 import QtCore, QtWidgets

from nyx.core.models.log_record_model import LogRecordListModel
from nyx.editor.widgets.output_log.output_log_dock import OutputLogDockWidget
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


def test_log_model_trims_to_maximum():
    model = LogRecordListModel(maximum_retained_log_record_count=3)
    for number in range(5):
        model.append_log_record(make_record(str(number)))
    assert model.rowCount() == 3
    assert model.latest_log_record().getMessage() == "4"
    assert model.index(0).data() == "2"


# ---- Dock ----
@pytest.fixture
def output_log_dock(qtbot):
    window = QtWidgets.QMainWindow()
    qtbot.addWidget(window)
    dock = OutputLogDockWidget("Log", window)
    window.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, dock)
    window.resize(600, 400)
    window.show()
    yield dock  # `window` stays alive in this frame


def _fake_config(is_expanded=False, expanded_height=250, minimum_level=logging.DEBUG):
    log_widget = types.SimpleNamespace(
        is_expanded=is_expanded,
        expanded_height=expanded_height,
        minimum_level=minimum_level,
    )
    return types.SimpleNamespace(
        values=types.SimpleNamespace(
            editor_widgets=types.SimpleNamespace(log_widget=log_widget)
        )
    )


def test_dock_collapsed_height_is_pinned_to_header(output_log_dock):
    header = output_log_dock.output_log_widget.header_height_in_pixels()
    assert output_log_dock.output_log_widget.minimumHeight() == header
    assert output_log_dock.output_log_widget.maximumHeight() == header


def test_dock_expanding_unpins_height(output_log_dock):
    output_log_dock.output_log_widget.set_expanded(True)
    assert output_log_dock.output_log_widget.maximumHeight() > 10_000
    assert output_log_dock.output_log_widget.minimumHeight() > (
        output_log_dock.output_log_widget.header_height_in_pixels()
    )


def test_dock_applies_and_saves_config(output_log_dock):
    output_log_dock.apply_config_values(
        _fake_config(is_expanded=True, expanded_height=300)
    )
    assert output_log_dock.output_log_widget.is_expanded()
    assert output_log_dock._last_user_expanded_height == 300

    saved = _fake_config(is_expanded=False, expanded_height=0)
    output_log_dock.save_config_values(saved)
    values = saved.values.editor_widgets.log_widget
    assert values.is_expanded is True
    assert values.expanded_height == 300


def test_dock_applies_and_saves_minimum_level(output_log_dock):
    output_log_dock.apply_config_values(_fake_config(minimum_level=logging.WARNING))
    assert output_log_dock.output_log_widget.get_minimum_level() == logging.WARNING
    assert (
        output_log_dock.output_log_widget._filter_model._minimum_level == logging.WARNING
    )

    saved = _fake_config(minimum_level=logging.DEBUG)
    output_log_dock.save_config_values(saved)
    assert saved.values.editor_widgets.log_widget.minimum_level == logging.WARNING


def test_dock_size_hint_uses_remembered_height_when_expanded(output_log_dock):
    output_log_dock.apply_config_values(
        _fake_config(is_expanded=True, expanded_height=321)
    )
    assert output_log_dock.sizeHint().height() == 321


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
