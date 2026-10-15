from unittest import mock

import pytest
from PySide6 import QtCore, QtWidgets

from nyx.editor.widgets.dialogs.popup_nodes_palette import PopupNodesPalette


@pytest.fixture
def no_exec(monkeypatch):
    """Replace the blocking `exec` with a recorder capturing the dialog."""
    captured = []

    def fake_exec(self):
        captured.append(self)
        return 0

    monkeypatch.setattr(PopupNodesPalette, "exec", fake_exec)
    return captured


def test_popup_centered_without_stage_graph_does_nothing(main_window, no_exec):
    assert PopupNodesPalette.popup_centered() is None
    assert no_exec == []


def test_popup_centered_is_centered_over_window(stage_editor, main_window, no_exec):
    palette = PopupNodesPalette.popup_centered()
    assert no_exec == [palette]
    assert palette.parent() is main_window
    assert palette.geometry().center() - main_window.geometry().center() in (
        QtCore.QPoint(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
    )


def test_popup_centered_passes_spawn_position_to_spawner(stage_editor, no_exec):
    position = QtCore.QPointF(33, 44)
    palette = PopupNodesPalette.popup_centered(position)
    assert palette._nodes_palette_view.nodes_spawner.spawn_position == position


def test_palette_is_modal_dialog_with_fixed_size(stage_editor, no_exec):
    palette = PopupNodesPalette.popup_centered()
    assert isinstance(palette, QtWidgets.QDialog)
    assert palette.size() == QtCore.QSize(400, 500)
    assert palette.testAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)


def test_spawned_node_closes_palette(stage_editor, no_exec, qtbot):
    from nyx.api.v1 import CoreNodes

    palette = PopupNodesPalette.popup_centered()
    destroyed = mock.Mock()
    palette.destroyed.connect(destroyed)

    palette._nodes_palette_view.nodes_spawner.spawnNode(CoreNodes.EMPTY)
    qtbot.waitUntil(lambda: destroyed.called, timeout=2000)
