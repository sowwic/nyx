import pytest
from PySide6 import QtCore, QtGui

from nyx.api.v1 import editor_utils
from nyx.editor.utils import common
from nyx.utils import icon_fn


@pytest.mark.parametrize("name", editor_utils.__all__)
def test_every_exported_helper_exists_and_is_callable(name):
    assert callable(getattr(editor_utils, name))


def test_helpers_are_the_ones_of_the_editor_and_utils():
    assert editor_utils.blocked_signals is common.blocked_signals
    assert editor_utils.note_to_html is common.note_to_html
    assert editor_utils.create_mono_icon is icon_fn.create_mono_icon


def test_editor_utils_is_exported_by_the_api():
    import nyx.api.v1 as api

    assert api.editor_utils is editor_utils
    assert "editor_utils" in api.__all__


def test_blocked_signals_works_through_the_api(qapp):
    obj = QtCore.QObject()
    with editor_utils.blocked_signals(obj):
        assert obj.signalsBlocked()
    assert not obj.signalsBlocked()


def test_mono_icon_can_be_made_through_the_api(qapp, tmp_path):
    image = QtGui.QImage(16, 16, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtCore.Qt.GlobalColor.transparent)
    image.setPixelColor(8, 8, QtGui.QColor(200, 0, 0))
    path = tmp_path / "dot.png"
    image.save(str(path))

    icon = editor_utils.create_mono_icon(path)

    assert not icon.isNull()
