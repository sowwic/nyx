from PySide6 import QtCore, QtGui

from nyx.editor.utils import common


def test_blocked_signals_restores_previous_state(qapp):
    first, second = QtCore.QObject(), QtCore.QObject()
    second.blockSignals(True)  # was already blocked: must stay blocked
    with common.blocked_signals(first, second):
        assert first.signalsBlocked() and second.signalsBlocked()
    assert not first.signalsBlocked()
    assert second.signalsBlocked()


def test_blocked_signals_restores_on_error(qapp):
    obj = QtCore.QObject()
    try:
        with common.blocked_signals(obj):
            raise ValueError
    except ValueError:
        pass
    assert not obj.signalsBlocked()


def test_resolve_to_source_index_through_proxy_chain(qapp):
    source = QtGui.QStandardItemModel()
    for text in ("a", "b", "c"):
        source.appendRow(QtGui.QStandardItem(text))
    first = QtCore.QSortFilterProxyModel()
    first.setSourceModel(source)
    first.setFilterFixedString("c")
    second = QtCore.QSortFilterProxyModel()
    second.setSourceModel(first)

    proxied = second.index(0, 0)
    assert proxied.data() == "c"
    resolved = common.resolve_to_source_index(proxied)
    assert resolved.model() is source
    assert resolved.row() == 2


def test_resolve_to_source_index_without_proxy_is_identity(qapp):
    model = QtGui.QStandardItemModel()
    model.appendRow(QtGui.QStandardItem("x"))
    index = model.index(0, 0)
    assert common.resolve_to_source_index(index) == index


def test_tooltip_html_escapes_values_and_skips_tooltip_role(qapp):
    model = QtGui.QStandardItemModel()
    item = QtGui.QStandardItem("<b>bold</b>")
    item.setToolTip("recursive")
    model.appendRow(item)

    html = common.build_role_tooltip_html(model.index(0, 0))
    assert "&lt;b&gt;bold&lt;/b&gt;" in html
    assert "<b>bold</b>" not in html
    assert "recursive" not in html


def test_tooltip_html_truncates_long_values(qapp):
    model = QtGui.QStandardItemModel()
    model.appendRow(QtGui.QStandardItem("x" * 500))
    html = common.build_role_tooltip_html(model.index(0, 0), maximum_value_length=20)
    assert "x" * 20 + "…" in html
    assert "x" * 21 not in html


def test_application_helpers(main_window, stage_editor, qapp):
    assert common.get_application_qml_engine() is qapp.qml_engine
    assert common.get_current_stage_graph() is stage_editor
