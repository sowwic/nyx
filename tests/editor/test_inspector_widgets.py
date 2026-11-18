import logging

import pytest
from PySide6 import QtCore, QtGui, QtWidgets

from nyx.api.v1 import (
    CoreInspectorWidgets,
    CoreNodes,
    CoreUtilObjects,
    NYX_REGISTRY,
    commands,
)
from nyx.api.v1.editor_utils import InspectorWidget
from nyx.editor.graphics.graphics_util_object import GraphicsUtilObject
from nyx.editor.views.node_components_view import NodeComponentsView
from nyx.editor.widgets.inspector_widgets import NodeInspectorWidget
from nyx.stdlib.inspector_widgets.group import GroupInspector
from nyx.stdlib.inspector_widgets.note import NoteInspector
from nyx.stdlib.util_objects.group import GroupObject
from nyx.stdlib.util_objects.note import NoteObject


@pytest.fixture
def inspector(main_window):
    return main_window.inspector


@pytest.fixture
def create_util_object(stage_editor):
    def _create(type_id=CoreUtilObjects.NOTE, position=(0, 0), node=None, **kwargs):
        command = commands.CreateUtilObjectCommand(
            stage_editor.stage, type_id, node=node, position=position, **kwargs
        )
        stage_editor.stage.push_command(command)
        return command.result_object

    return _create


@pytest.fixture
def note(create_util_object):
    return create_util_object(CoreUtilObjects.NOTE)


@pytest.fixture
def group(create_util_object):
    return create_util_object(CoreUtilObjects.GROUP, position=(400, 0))


def select_util_object(stage_editor, *util_objects):
    """Select exactly these util objects in the scene, and no node."""
    stage_editor.selection_model.clearSelection()
    gr_stage = stage_editor.gr_stage
    for gr_util in gr_stage.selected_gr_util_objects():
        gr_util.setSelected(False)
    for util_object in util_objects:
        gr_stage.get_gr_util_object(util_object).setSelected(True)


def select_node(stage_editor, node):
    stage_editor.select_nodes([node])


def test_the_builtin_widgets_are_registered():
    assert NYX_REGISTRY.get_inspector_widget_cls(CoreInspectorWidgets.NODE) is (
        NodeInspectorWidget
    )
    assert NYX_REGISTRY.get_inspector_widget_cls(CoreInspectorWidgets.NOTE) is (
        NoteInspector
    )
    assert NYX_REGISTRY.get_inspector_widget_cls(CoreInspectorWidgets.GROUP) is (
        GroupInspector
    )


def test_the_node_widget_exists_before_anything_is_selected(inspector):
    assert isinstance(inspector.findChild(NodeInspectorWidget), NodeInspectorWidget)
    assert inspector.findChild(NodeComponentsView) is not None


def test_without_an_editor_the_inspector_is_disabled_with_a_placeholder(
    main_window, inspector
):
    inspector.update_data()

    assert not inspector.isEnabled()
    assert inspector.active_widget is None
    assert inspector.placeholder_text == "Nothing to inspect."


def test_nothing_selected_shows_the_root_node(inspector, stage_editor):
    stage_editor.selection_model.clearSelection()
    inspector.update_data()

    assert isinstance(inspector.active_widget, NodeInspectorWidget)
    assert inspector.active_widget.stage_object is stage_editor.stage.root_node


def test_a_selected_node_is_shown_by_the_node_widget(
    inspector, stage_editor, create_node
):
    node = create_node(stage_editor.stage, "a", type_id=CoreNodes.EMPTY)

    select_node(stage_editor, node)

    assert isinstance(inspector.active_widget, NodeInspectorWidget)
    assert inspector.active_widget.stage_object is node


def test_a_selected_note_is_shown_by_the_note_widget(inspector, stage_editor, note):
    select_util_object(stage_editor, note)

    assert isinstance(inspector.active_widget, NoteInspector)
    assert inspector.active_widget.stage_object is note


def test_a_selected_group_is_shown_by_the_group_widget(inspector, stage_editor, group):
    select_util_object(stage_editor, group)

    assert isinstance(inspector.active_widget, GroupInspector)
    assert inspector.active_widget.stage_object is group


def test_deselecting_goes_back_to_the_root_node(inspector, stage_editor, note):
    select_util_object(stage_editor, note)
    select_util_object(stage_editor)

    assert isinstance(inspector.active_widget, NodeInspectorWidget)
    assert inspector.active_widget.stage_object is stage_editor.stage.root_node


def test_nodes_come_before_util_objects(inspector, stage_editor, create_node, note):
    node = create_node(stage_editor.stage, "a", type_id=CoreNodes.EMPTY)
    select_util_object(stage_editor, note)

    select_node(stage_editor, node)
    stage_editor.gr_stage.get_gr_util_object(note).setSelected(True)

    assert stage_editor.list_selected_objects() == [node, note]
    assert isinstance(inspector.active_widget, NodeInspectorWidget)
    assert inspector.active_widget.stage_object is node


def test_selected_objects_changed_is_never_emitted_twice_for_the_same_selection(
    stage_editor, create_node, note, group
):
    node = create_node(stage_editor.stage, "a", type_id=CoreNodes.EMPTY)
    stage_editor.selection_model.clearSelection()
    select_util_object(stage_editor)
    selections = []
    stage_editor.selected_objects_changed.connect(
        lambda: selections.append(stage_editor.list_selected_objects())
    )

    select_util_object(stage_editor, note)
    assert selections == [[note]]

    stage_editor.notify_selected_objects_changed()
    assert selections == [[note]]

    select_node(stage_editor, node)
    assert selections[-1] == [node, note]

    select_util_object(stage_editor, group)
    assert selections[-1] == [group]
    assert all(first != second for first, second in zip(selections, selections[1:]))


def test_an_object_without_an_inspector_widget_gets_a_placeholder(
    inspector, stage_editor, create_node
):
    node = create_node(stage_editor.stage, "a", type_id=CoreNodes.ACTION)
    component = node["flow"]
    assert component.get_inspector_widget_id() is None

    inspector.show_stage_object(component)

    assert inspector.active_widget is None
    assert inspector.main_layout.currentWidget() is inspector._placeholder
    assert inspector.placeholder_text.startswith("No inspector available for")


def test_an_unregistered_widget_id_gives_a_placeholder_and_one_error(
    inspector, stage_editor, note, monkeypatch, caplog
):
    monkeypatch.setattr(
        NoteObject, "get_inspector_widget_id", classmethod(lambda cls: "test.missing")
    )

    with caplog.at_level(logging.ERROR):
        inspector.show_stage_object(note)
        inspector.show_stage_object(note)

    assert inspector.active_widget is None
    assert "test.missing" in inspector.placeholder_text
    assert caplog.text.count("Unknown inspector widget 'test.missing'") == 1


class CustomInspector(InspectorWidget):
    refreshed = []
    cleared = []

    @classmethod
    def get_type_id(cls) -> str:
        return "test.custom_inspector"

    def refresh(self) -> None:
        CustomInspector.refreshed.append(self.stage_object)

    def clear(self) -> None:
        CustomInspector.cleared.append(True)


@pytest.fixture
def custom_inspector_registered(inspector):
    CustomInspector.refreshed.clear()
    CustomInspector.cleared.clear()
    NYX_REGISTRY.inspector_widgets[CustomInspector.get_type_id()] = CustomInspector
    yield CustomInspector
    NYX_REGISTRY.inspector_widgets.pop(CustomInspector.get_type_id(), None)
    widget = inspector._widgets.pop(CustomInspector.get_type_id(), None)
    if widget is not None:
        inspector.main_layout.removeWidget(widget)
        widget.deleteLater()


def test_a_plugin_widget_shows_the_objects_of_its_type(
    inspector,
    stage_editor,
    group,
    custom_inspector_registered,
    monkeypatch,
):
    monkeypatch.setattr(
        GroupObject,
        "get_inspector_widget_id",
        classmethod(lambda cls: CustomInspector.get_type_id()),
    )

    select_util_object(stage_editor, group)

    assert isinstance(inspector.active_widget, CustomInspector)
    assert CustomInspector.refreshed[-1] is group


def test_the_widget_shown_before_is_told_to_show_nothing(
    inspector,
    stage_editor,
    group,
    custom_inspector_registered,
    monkeypatch,
):
    monkeypatch.setattr(
        GroupObject,
        "get_inspector_widget_id",
        classmethod(lambda cls: CustomInspector.get_type_id()),
    )
    select_util_object(stage_editor, group)
    CustomInspector.cleared.clear()

    select_util_object(stage_editor)

    assert CustomInspector.cleared == [True]
    assert isinstance(inspector.active_widget, NodeInspectorWidget)


def test_widgets_let_go_of_deleted_objects(inspector, stage_editor, note):
    select_util_object(stage_editor, note)
    widget = inspector.active_widget

    stage_editor.stage.push_command(
        commands.DeleteUtilObjectCommand(stage_editor.stage, [note])
    )

    assert widget.stage_object is None
    assert isinstance(inspector.active_widget, NodeInspectorWidget)


# ---- Note ----
def test_the_note_widget_shows_the_text_and_color(inspector, stage_editor, note):
    stage_editor.stage.push_command(
        commands.SetUtilObjectPropertiesCommand(
            stage_editor.stage, {note: {"text": "hello", "color": "#5b8def"}}
        )
    )

    select_util_object(stage_editor, note)
    widget = inspector.active_widget

    assert widget.text_edit.toPlainText() == "hello"
    assert widget.color_combo.currentText() == "Blue"
    assert widget.type_label.text() == "Note"
    assert widget.path_label.text() == str(note.path)


def test_the_note_and_group_widgets_show_their_own_icons(
    inspector, stage_editor, note, group
):
    assert NoteObject.get_type_icon() == ":/icons/sticky_note"
    assert GroupObject.get_type_icon() == ":/icons/group"

    for util_object in (note, group):
        select_util_object(stage_editor, util_object)
        shown = inspector.active_widget.icon_label.pixmap().toImage()
        expected = QtGui.QIcon(type(util_object).get_type_icon()).pixmap(24, 24)
        assert shown == expected.toImage()


def test_editing_the_note_text_is_one_undoable_command(inspector, stage_editor, note):
    select_util_object(stage_editor, note)
    widget = inspector.active_widget
    undo_count = stage_editor.stage.undo_stack.count()

    widget.text_edit.setPlainText("typed")
    widget.text_edit.editing_finished.emit()

    assert note.text == "typed"
    assert stage_editor.stage.undo_stack.count() == undo_count + 1
    assert widget.text_edit.toPlainText() == "typed"

    stage_editor.stage.undo_stack.undo()
    assert note.text == ""
    assert widget.text_edit.toPlainText() == ""


def test_finishing_without_a_change_pushes_nothing(inspector, stage_editor, note):
    select_util_object(stage_editor, note)
    widget = inspector.active_widget
    undo_count = stage_editor.stage.undo_stack.count()

    widget.text_edit.editing_finished.emit()

    assert stage_editor.stage.undo_stack.count() == undo_count


def test_the_text_just_committed_is_not_reset_by_the_refresh(
    inspector, stage_editor, note
):
    select_util_object(stage_editor, note)
    widget = inspector.active_widget
    widget.text_edit.setPlainText("typed")
    widget.text_edit.editing_finished.emit()
    cursor = widget.text_edit.textCursor()
    cursor.setPosition(2)
    widget.text_edit.setTextCursor(cursor)

    inspector.update_data()

    assert widget.text_edit.toPlainText() == "typed"
    assert widget.text_edit.textCursor().position() == 2


def test_choosing_a_note_color_is_undoable(inspector, stage_editor, note):
    select_util_object(stage_editor, note)
    widget = inspector.active_widget
    old_color = note.color
    index = widget.color_combo.findText("Green")

    widget.color_combo.activated.emit(index)

    assert note.color == GraphicsUtilObject.COLOR_PRESETS["Green"]
    stage_editor.stage.undo_stack.undo()
    assert note.color == old_color


def test_a_color_that_is_not_a_preset_is_shown_as_custom(inspector, stage_editor, note):
    stage_editor.stage.push_command(
        commands.SetUtilObjectPropertiesCommand(
            stage_editor.stage, {note: {"color": "#123456"}}
        )
    )

    select_util_object(stage_editor, note)
    combo = inspector.active_widget.color_combo

    assert combo.currentText() == "Custom"
    assert combo.currentData() == "#123456"

    combo.activated.emit(combo.findText("Red"))
    assert combo.findText("Custom") == -1
    assert combo.currentText() == "Red"


def test_a_locked_note_cannot_be_changed(inspector, stage_editor, note, monkeypatch):
    monkeypatch.setattr(NoteObject, "is_locked", property(lambda self: True))
    select_util_object(stage_editor, note)
    widget = inspector.active_widget
    undo_count = stage_editor.stage.undo_stack.count()

    widget.text_edit.setPlainText("nope")
    widget.text_edit.editing_finished.emit()

    assert not widget.form_container.isEnabled()
    assert not widget.locked_label.isHidden()
    assert note.text == ""
    assert stage_editor.stage.undo_stack.count() == undo_count


def test_text_typed_before_the_selection_changes_is_not_lost(
    inspector, stage_editor, note
):
    select_util_object(stage_editor, note)
    inspector.active_widget.text_edit.setPlainText("typed, not finished")

    select_util_object(stage_editor)

    assert note.text == "typed, not finished"


# ---- Group ----
def test_the_group_widget_shows_and_changes_the_title(inspector, stage_editor, group):
    select_util_object(stage_editor, group)
    widget = inspector.active_widget
    assert widget.title_edit.text() == group.title
    assert widget.type_label.text() == "Group"

    widget.title_edit.setText("Inputs")
    widget.title_edit.editingFinished.emit()

    assert group.title == "Inputs"
    stage_editor.stage.undo_stack.undo()
    assert group.title == GroupObject.DEFAULT_TITLE
    assert widget.title_edit.text() == GroupObject.DEFAULT_TITLE


def test_choosing_a_group_color_is_undoable(inspector, stage_editor, group):
    select_util_object(stage_editor, group)
    widget = inspector.active_widget
    old_color = group.color

    widget.color_combo.activated.emit(widget.color_combo.findText("Purple"))

    assert group.color == GraphicsUtilObject.COLOR_PRESETS["Purple"]
    stage_editor.stage.undo_stack.undo()
    assert group.color == old_color


def test_switching_between_a_note_and_a_group_swaps_the_widget(
    inspector, stage_editor, note, group
):
    select_util_object(stage_editor, note)
    note_widget = inspector.active_widget
    select_util_object(stage_editor, group)
    group_widget = inspector.active_widget

    assert isinstance(note_widget, NoteInspector)
    assert isinstance(group_widget, GroupInspector)
    assert inspector.main_layout.currentWidget() is group_widget
    assert note_widget.stage_object is None
    assert isinstance(group_widget, QtWidgets.QWidget)
    assert inspector._widgets[CoreInspectorWidgets.NOTE] is note_widget
    assert QtCore.QObject.parent(note_widget) is not None
