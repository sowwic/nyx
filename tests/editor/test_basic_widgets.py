from PySide6 import QtCore, QtWidgets

from nyx.editor.widgets.common_widgets import ClickableHeaderWidget, ElidedTextLabel
from nyx.editor.widgets.dim_overlay import DimOverlay, dimmed_ovelay
from nyx.editor.widgets.stage_mdi_area import StageMdiArea
from nyx.editor.widgets.stage_mdi_window import StageMdiSubWindow
from nyx.editor.widgets.text_edit_widget import NyxTextEdit


# ---- DimOverlay ----
def test_dim_overlay_covers_target_and_follows_resize(qtbot):
    target = QtWidgets.QWidget()
    qtbot.addWidget(target)
    target.resize(200, 100)
    target.show()

    with dimmed_ovelay(target):
        overlay = target.findChild(DimOverlay)
        assert overlay is not None
        assert overlay.isVisible()
        assert overlay.geometry() == target.rect()
        target.resize(300, 150)
        assert overlay.geometry() == target.rect()

    assert not overlay.isVisible()


def test_dim_overlay_removed_even_if_body_raises(qtbot):
    target = QtWidgets.QWidget()
    qtbot.addWidget(target)
    target.show()
    try:
        with dimmed_ovelay(target):
            raise RuntimeError
    except RuntimeError:
        pass
    qtbot.waitUntil(lambda: target.findChild(DimOverlay) is None, timeout=2000)


# ---- common widgets ----
def test_elided_label_elides_and_keeps_full_text_in_tooltip(qtbot):
    label = ElidedTextLabel()
    qtbot.addWidget(label)
    full_text = "a very long message " * 10
    label.resize(60, 20)
    label.show()
    label.set_full_text(full_text)

    assert label.toolTip() == full_text
    assert label.text().endswith("…")
    assert len(label.text()) < len(full_text)

    label.resize(5000, 20)
    assert label.text() == full_text


def test_clickable_header_emits_only_on_left_click(qtbot):
    header = ClickableHeaderWidget()
    qtbot.addWidget(header)
    header.show()

    with qtbot.waitSignal(header.clicked, timeout=1000):
        qtbot.mouseClick(header, QtCore.Qt.MouseButton.LeftButton)
    with qtbot.assertNotEmitted(header.clicked):
        qtbot.mouseClick(header, QtCore.Qt.MouseButton.RightButton)


# ---- NyxTextEdit ----
def _text_edit_with_neighbor(qtbot):
    window = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(window)
    edit = NyxTextEdit()
    other = QtWidgets.QLineEdit()
    layout.addWidget(edit)
    layout.addWidget(other)
    qtbot.addWidget(window)
    edit._window_ref = window  # keep the Python wrapper (and C++ window) alive
    return edit, other


def test_text_edit_emits_editing_finished_when_changed_and_focus_lost(qtbot, give_focus):
    edit, other = _text_edit_with_neighbor(qtbot)
    give_focus(edit)
    edit.setPlainText("changed")
    with qtbot.waitSignal(edit.editingFinished, timeout=1000):
        give_focus(other)


def test_text_edit_silent_when_unchanged(qtbot, give_focus):
    edit, other = _text_edit_with_neighbor(qtbot)
    give_focus(edit)
    edit.set_text_changed(False)
    with qtbot.assertNotEmitted(edit.editingFinished):
        give_focus(other)


def test_text_edit_emits_received_focus(qtbot, give_focus):
    edit, _other = _text_edit_with_neighbor(qtbot)
    with qtbot.waitSignal(edit.receivedFocus, timeout=1000):
        give_focus(edit)


# ---- MDI ----
def test_mdi_area_wraps_widgets_in_stage_sub_windows(qtbot):
    area = StageMdiArea()
    qtbot.addWidget(area)
    area.show()
    content = QtWidgets.QLabel("stage")

    sub_window = area.addSubWindow(content)

    assert isinstance(sub_window, StageMdiSubWindow)
    assert sub_window.widget() is content
    assert sub_window.testAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
    assert area.subWindowList() == [sub_window]


def test_mdi_area_paints_placeholder_when_empty_and_not_when_filled(qtbot):
    area = StageMdiArea()
    qtbot.addWidget(area)
    area.resize(400, 300)
    area.show()
    empty_image = area.grab().toImage()

    area.addSubWindow(QtWidgets.QLabel("stage")).show()
    filled_image = area.grab().toImage()

    assert not empty_image.isNull()
    assert empty_image != filled_image
