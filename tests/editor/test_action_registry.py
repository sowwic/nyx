import pytest
from PySide6 import QtGui, QtWidgets

from nyx.core.exceptions import ActionLookupError, ActionRegistrationError
from nyx.editor.core.action_registry import ActionDefinition, ActionRegistry
from nyx.editor.core.actions import ActionId, register_default_actions


@pytest.fixture
def registry(qtbot) -> ActionRegistry:
    registry = ActionRegistry()
    register_default_actions(registry)
    return registry


# ---- Definitions ----
def test_all_action_ids_registered(registry):
    register_default_actions(registry)  # idempotent
    for action_id in ActionId:
        assert registry.has_definition(action_id)


def test_unknown_and_duplicate(registry):
    with pytest.raises(ActionLookupError):
        registry.get_definition("nope")
    with pytest.raises(ActionLookupError):
        registry.action("nope")
    with pytest.raises(ActionRegistrationError):
        registry.register_definition(registry.get_definition(ActionId.COPY))


def test_iter_definitions_filters_by_category(registry):
    edit = list(registry.iter_definitions("Edit"))
    assert edit
    assert all(d.category == "Edit" for d in edit)
    assert len(list(registry.iter_definitions())) == len(ActionId)


def test_clear_removes_everything(registry):
    registry.action(ActionId.COPY)
    registry.clear()
    assert not registry.has_definition(ActionId.COPY)
    assert list(registry.iter_actions()) == []


# ---- Shared QAction ----
def test_shared_action_matches_definition(registry):
    definition = registry.get_definition(ActionId.SAVE_STAGE)
    action = registry.action(ActionId.SAVE_STAGE)
    assert action is registry.action(ActionId.SAVE_STAGE)
    assert action.text() == definition.text
    assert action.objectName() == ActionId.SAVE_STAGE
    assert action.shortcut() == QtGui.QKeySequence(definition.default_shortcut)


def test_icon_and_status_tip_applied(registry):
    registry.register_definition(
        ActionDefinition("test.tip", "Tip", status_tip="hello", icon_path=None)
    )
    action = registry.action("test.tip")
    assert action.statusTip() == action.toolTip() == "hello"


# ---- Shortcuts ----
def test_shortcut_override_reaches_shared_action(registry):
    registry.set_shortcut_override(ActionId.COPY, "Ctrl+Shift+C")
    assert registry.get_shortcut_text(ActionId.COPY) == "Ctrl+Shift+C"
    assert registry.action(ActionId.COPY).shortcut().toString() == "Ctrl+Shift+C"


def test_override_applied_to_lazily_created_action(registry):
    registry.set_shortcut_override(ActionId.COPY, "Ctrl+Shift+C")
    assert registry.action(ActionId.COPY).shortcut().toString() == "Ctrl+Shift+C"


def test_reset_shortcut_restores_default(registry):
    action = registry.action(ActionId.COPY)
    registry.set_shortcut_override(ActionId.COPY, "")
    assert action.shortcut().isEmpty()
    registry.reset_shortcut(ActionId.COPY)
    assert action.shortcut().toString() == "Ctrl+C"


def test_export_import_roundtrip_ignores_unknown(registry, caplog):
    registry.set_shortcut_override(ActionId.COPY, "Ctrl+Alt+C")
    exported = registry.export_shortcut_overrides()
    assert exported == {ActionId.COPY: "Ctrl+Alt+C"}

    other = ActionRegistry()
    register_default_actions(other)
    other.import_shortcut_overrides({**exported, "bogus.id": "X"})
    assert other.get_shortcut_text(ActionId.COPY) == "Ctrl+Alt+C"
    assert "bogus.id" not in other.export_shortcut_overrides()


def test_adopt_action_gets_shortcut_and_overrides(registry, qtbot):
    parent = QtWidgets.QWidget()
    qtbot.addWidget(parent)
    external = QtGui.QAction("Undo", parent)
    registry.adopt_action(ActionId.UNDO, external)
    assert external.shortcut().toString() == "Ctrl+Z"
    registry.set_shortcut_override(ActionId.UNDO, "Ctrl+Alt+Z")
    assert external.shortcut().toString() == "Ctrl+Alt+Z"


def test_adopt_replaces_existing_shared_action(registry, qtbot):
    parent = QtWidgets.QWidget()
    qtbot.addWidget(parent)
    shared = registry.action(ActionId.UNDO)
    registry.adopt_action(ActionId.UNDO, QtGui.QAction("Undo", parent))
    assert shared.shortcut().isEmpty()  # no duplicate shortcut left behind
    assert registry.action(ActionId.UNDO) is not shared


def test_action_created_signal_and_lookup_helpers(registry, qtbot):
    assert registry.existing_action(ActionId.COPY) is None
    with qtbot.waitSignal(registry.action_created) as blocker:
        action = registry.action(ActionId.COPY)
    assert blocker.args == [ActionId.COPY, action]
    assert registry.existing_action(ActionId.COPY) is action
    assert dict(registry.iter_actions()) == {ActionId.COPY: action}
    registry.action(ActionId.COPY)  # cached: no second signal


def test_cleared_signal(registry, qtbot):
    with qtbot.waitSignal(registry.cleared):
        registry.clear()


def test_attach_shortcuts_adds_every_action_to_widget(registry, qtbot):
    widget = QtWidgets.QWidget()
    qtbot.addWidget(widget)
    registry.attach_shortcuts(widget)
    assert len(widget.actions()) == len(ActionId)
