import logging
import types

from nyx.api.v1 import (
    CoreInspectorWidgets,
    Link,
    Node,
    NodeComponent,
    StageObject,
    UtilObject,
)
from nyx.core.plugin_subsystem.plugin import NyxPluginContents
from nyx.core.plugin_subsystem.registry import NyxRegistry
from nyx.stdlib.util_objects.group import GroupObject
from nyx.stdlib.util_objects.note import NoteObject


class FakeInspectorWidget:
    ID = "test.fake_inspector"

    @classmethod
    def get_type_id(cls) -> str:
        return cls.ID


class OtherFakeInspectorWidget(FakeInspectorWidget):
    pass


def plugin_entry(*widget_classes):
    contents = types.SimpleNamespace(inspector_widgets=list(widget_classes))
    return types.SimpleNamespace(
        plugin_instance=types.SimpleNamespace(contents=contents),
        plugin_cls=types.SimpleNamespace(get_type_id=lambda: "test:plugin"),
    )


def test_core_inspector_widget_ids_are_unique_and_dotted():
    ids = [widget_id.value for widget_id in CoreInspectorWidgets]

    assert len(set(ids)) == len(ids)
    assert all(widget_id.startswith("core.") for widget_id in ids)


def test_stage_objects_have_no_inspector_widget_by_default():
    assert StageObject.get_inspector_widget_id() is None
    assert NodeComponent.get_inspector_widget_id() is None
    assert Link.get_inspector_widget_id() is None
    assert UtilObject.get_inspector_widget_id() is None


def test_nodes_and_the_util_objects_of_the_stdlib_name_their_widgets():
    assert Node.get_inspector_widget_id() == CoreInspectorWidgets.NODE
    assert NoteObject.get_inspector_widget_id() == CoreInspectorWidgets.NOTE
    assert GroupObject.get_inspector_widget_id() == CoreInspectorWidgets.GROUP


def test_a_subclass_sets_the_inspector_widget_id_of_its_type():
    class Custom(UtilObject):
        @classmethod
        def get_inspector_widget_id(cls) -> str | None:
            return "test.custom"

    assert Custom.get_inspector_widget_id() == "test.custom"
    assert UtilObject.get_inspector_widget_id() is None


def test_the_inspector_widget_id_is_not_saved():
    assert "inspector_widget_id" not in NoteObject().serialize()


def test_plugin_contents_start_without_inspector_widgets():
    contents = NyxPluginContents()

    assert contents.inspector_widgets == []
    assert NyxPluginContents().inspector_widgets is not contents.inspector_widgets


def test_a_plugin_widget_is_registered_and_found_by_id():
    registry = NyxRegistry()

    registry.register_inspector_widgets(plugin_entry(FakeInspectorWidget))

    assert (
        registry.get_inspector_widget_cls(FakeInspectorWidget.ID) is FakeInspectorWidget
    )
    assert registry.get_inspector_widget_cls("test.nope") is None


def test_the_first_widget_with_an_id_wins_and_the_second_is_reported(caplog):
    registry = NyxRegistry()

    with caplog.at_level(logging.ERROR):
        registry.register_inspector_widgets(
            plugin_entry(FakeInspectorWidget, OtherFakeInspectorWidget)
        )

    assert (
        registry.get_inspector_widget_cls(FakeInspectorWidget.ID) is FakeInspectorWidget
    )
    assert "OtherFakeInspectorWidget" in caplog.text
    assert FakeInspectorWidget.ID in caplog.text


def test_a_plugin_cannot_replace_a_builtin_widget(caplog):
    registry = NyxRegistry()
    registry.register_builtin_inspector_widget(
        FakeInspectorWidget.ID, FakeInspectorWidget
    )

    with caplog.at_level(logging.ERROR):
        registry.register_inspector_widgets(plugin_entry(OtherFakeInspectorWidget))

    assert (
        registry.get_inspector_widget_cls(FakeInspectorWidget.ID) is FakeInspectorWidget
    )


def test_reset_keeps_only_the_builtin_widgets():
    registry = NyxRegistry()
    registry.register_builtin_inspector_widget("test.builtin", FakeInspectorWidget)
    registry.register_inspector_widgets(plugin_entry(OtherFakeInspectorWidget))
    assert FakeInspectorWidget.ID in registry.inspector_widgets

    registry.reset_inspector_widgets()

    assert list(registry.inspector_widgets) == ["test.builtin"]


def test_clear_drops_plugin_widgets_but_keeps_the_builtin_ones():
    registry = NyxRegistry()
    registry.register_builtin_inspector_widget("test.builtin", FakeInspectorWidget)
    registry.register_inspector_widgets(plugin_entry(OtherFakeInspectorWidget))

    registry.clear()

    assert list(registry.inspector_widgets) == ["test.builtin"]


def test_register_plugin_content_rebuilds_the_widgets_of_the_enabled_plugins():
    registry = NyxRegistry()
    registry.register_builtin_inspector_widget("test.builtin", FakeInspectorWidget)
    registry.inspector_widgets["test.stale"] = OtherFakeInspectorWidget

    registry.register_plugin_content()

    assert list(registry.inspector_widgets) == ["test.builtin"]
