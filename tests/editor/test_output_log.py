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
def dock(qtbot):
    window = QtWidgets.QMainWindow()
    qtbot.addWidget(window)
    dock = OutputLogDockWidget("Log", window)
    window.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, dock)
    window.resize(600, 400)
    window.show()
    yield dock  # `window` stays alive in this frame


def _fake_config(is_expanded=False, expanded_height=250):
    log_widget = types.SimpleNamespace(
        is_expanded=is_expanded, expanded_height=expanded_height
    )
    return types.SimpleNamespace(
        values=types.SimpleNamespace(
            editor_widgets=types.SimpleNamespace(log_widget=log_widget)
        )
    )


def test_dock_collapsed_height_is_pinned_to_header(dock):
    header = dock.output_log_widget.header_height_in_pixels()
    assert dock.output_log_widget.minimumHeight() == header
    assert dock.output_log_widget.maximumHeight() == header


def test_dock_expanding_unpins_height(dock):
    dock.output_log_widget.set_expanded(True)
    assert dock.output_log_widget.maximumHeight() > 10_000
    assert dock.output_log_widget.minimumHeight() > (
        dock.output_log_widget.header_height_in_pixels()
    )


def test_dock_applies_and_saves_config(dock):
    dock.apply_config_values(_fake_config(is_expanded=True, expanded_height=300))
    assert dock.output_log_widget.is_expanded()
    assert dock._last_user_expanded_height == 300

    saved = _fake_config(is_expanded=False, expanded_height=0)
    dock.save_config_values(saved)
    values = saved.values.editor_widgets.log_widget
    assert values.is_expanded is True
    assert values.expanded_height == 300


def test_dock_size_hint_uses_remembered_height_when_expanded(dock):
    dock.apply_config_values(_fake_config(is_expanded=True, expanded_height=321))
    assert dock.sizeHint().height() == 321
