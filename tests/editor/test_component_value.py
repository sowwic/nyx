import pytest
from PySide6 import QtCore, QtQml, QtWidgets

from nyx.api.v1 import CoreNodeComponents, CoreNodes, commands
from nyx.editor.controllers.components import ComponentsController
from nyx.editor.views.node_components_view import NodeComponentsView

from nyx.static.paths import PACKAGE_ROOT

_KEEP_ALIVE = []
CORE_QML_DIR = PACKAGE_ROOT / "plugins" / "core" / "qml" / "NyxCore"


class ControllerStub(QtCore.QObject):
    """Records the calls the editors make on the components controller."""

    def __init__(self):
        super().__init__()
        self.calls = []
        self.file_dialogs = []
        self.chosen_file = ""

    @QtCore.Slot(int, str, bool)
    def setComponentValue(self, row, new_value, raw):
        self.calls.append((row, new_value, raw))

    @QtCore.Slot(str, str, str, result=str)
    def selectFile(self, title, name_filters, start_path):
        self.file_dialogs.append((title, name_filters, start_path))
        return self.chosen_file


class RootStub(QtCore.QObject):
    """Stands in for the `root` id of the components view."""

    def __init__(self, controller):
        super().__init__()
        self._controller = controller

    @QtCore.Property(QtCore.QObject, constant=True)
    def componentsController(self):
        return self._controller


def make_component(**overrides):
    component = {
        "index": 3,
        "rawValue": "1+1",
        "cachedValue": 2,
        "displayValue": "2",
        "isEditable": True,
        "inputLinks": [],
    }
    component.update(overrides)
    return component


class Editor:
    """Instantiated QML editor with helpers to drive it."""

    def __init__(self, qapp, qml_file, component, source=None):
        self.controller = ControllerStub()
        self._root = RootStub(self.controller)
        self.engine = qapp.qml_engine
        self.context = QtQml.QQmlContext(self.engine.rootContext())
        self.context.setContextProperty("root", self._root)
        # The component has to outlive the item it created.
        url = QtCore.QUrl.fromLocalFile(str(qml_file))
        if source is None:
            self._qml_component = QtQml.QQmlComponent(self.engine, url)
        else:
            self._qml_component = QtQml.QQmlComponent(self.engine)
            self._qml_component.setData(source.encode(), url)
        self.item = self._qml_component.create(self.context)
        assert self.item is not None, self._qml_component.errorString()
        self.item.setProperty("component", component)

    def run(self, expression):
        value, failed = QtQml.QQmlExpression(
            self.context, self.item, expression
        ).evaluate()
        return value

    def prop(self, name):
        return self.item.property(name)

    @property
    def field(self):
        return self.prop("field")

    @property
    def text(self):
        return self.field.property("text")


@pytest.fixture
def make_editor(qapp):
    editors = []

    def _make(qml_file, source=None, **component_overrides):
        editor = Editor(
            qapp, qml_file, make_component(**component_overrides), source=source
        )
        editors.append(editor)
        return editor

    yield _make
    for editor in editors:
        editor.item.deleteLater()
        editor.context.deleteLater()
        # The stubs have to outlive the items, or their bindings see `root` as null.
        _KEEP_ALIVE.append(editor)


@pytest.fixture
def value_editor(make_editor):
    return make_editor(CORE_QML_DIR / "ValueComponentItem.qml")


def test_editor_shows_display_value_read_only_by_default(value_editor):
    assert value_editor.text == "2"
    assert value_editor.prop("editing") is False
    assert value_editor.prop("field").property("readOnly") is True


def test_edit_request_switches_to_raw_value(value_editor):
    requested = []
    value_editor.item.editRequested.connect(lambda: requested.append(1))

    value_editor.run("requestEdit()")
    assert requested == [1]
    assert value_editor.prop("editing") is True
    assert value_editor.text == "1+1"  # what the user typed, not what it evaluated to
    assert value_editor.prop("field").property("readOnly") is False


def test_finishing_edit_sets_value_and_returns_to_display(value_editor):
    value_editor.run("requestEdit()")
    value_editor.run("finishEdit('2+2')")

    assert value_editor.controller.calls == [(3, "2+2", False)]  # evaluated
    assert value_editor.prop("editing") is False
    assert value_editor.text == "2"


def test_finishing_edit_with_unchanged_raw_text_sets_nothing(value_editor):
    value_editor.run("requestEdit()")
    value_editor.run("finishEdit('1+1')")
    assert value_editor.controller.calls == []
    assert value_editor.prop("editing") is False


def test_cancelling_edit_drops_typed_text(value_editor):
    value_editor.run("requestEdit()")
    value_editor.prop("field").setProperty("text", "garbage")
    value_editor.run("cancelEdit()")

    assert value_editor.controller.calls == []
    assert value_editor.prop("editing") is False
    assert value_editor.text == "2"


def test_edit_finished_signal_carries_typed_value(value_editor):
    finished = []
    value_editor.item.editFinished.connect(finished.append)
    value_editor.run("requestEdit()")
    value_editor.run("finishEdit('x')")
    assert finished == ["x"]


def test_non_editable_component_ignores_edit_request(make_editor):
    editor = make_editor(CORE_QML_DIR / "ValueComponentItem.qml", isEditable=False)
    editor.run("requestEdit()")
    assert editor.prop("editing") is False
    editor.run("finishEdit('x')")
    assert editor.controller.calls == []


def test_value_with_input_link_is_not_editable(make_editor):
    editor = make_editor(CORE_QML_DIR / "ValueComponentItem.qml", inputLinks=["a.b"])
    editor.run("requestEdit()")
    assert editor.prop("editing") is False


def test_value_editor_ignores_missing_component(make_editor):
    editor = make_editor(CORE_QML_DIR / "ValueComponentItem.qml")
    editor.item.setProperty("component", None)
    assert editor.prop("maskedText") == ""
    editor.run("requestEdit()")
    assert editor.prop("editing") is False


@pytest.mark.parametrize(
    "mask, expected",
    # ComponentValue.ValueMask: Display = 0, Raw = 1, Cached = 2
    [(0, "2"), (1, "1+1"), (2, "2")],
)
def test_masks_select_which_value_is_shown(value_editor, mask, expected):
    assert value_editor.run(f"textOf({mask})") == expected


def test_comment_is_multiline_and_sets_value_without_evaluating(make_editor):
    editor = make_editor(
        CORE_QML_DIR / "CommentComponentItem.qml", rawValue="a\nb", displayValue="a\nb"
    )
    assert editor.field.metaObject().className().startswith("TextArea")
    assert editor.text == "a\nb"

    editor.run("requestEdit()")
    editor.run("finishEdit('changed')")
    assert editor.controller.calls == [(3, "changed", True)]


def test_script_sets_value_without_evaluating(make_editor):
    editor = make_editor(
        CORE_QML_DIR / "ScriptComponentItem.qml",
        rawValue="pkg.mod:main",
        displayValue="",
    )
    editor.run("requestEdit()")
    assert editor.text == "pkg.mod:main"
    editor.run("finishEdit('other:run')")
    assert editor.controller.calls == [(3, "other:run", True)]


def test_edit_request_handled_by_implementation_when_auto_begin_is_off(value_editor):
    value_editor.item.setProperty("autoBeginEdit", False)
    value_editor.run("requestEdit()")
    assert value_editor.prop("editing") is False


def _walk(item):
    yield item
    for child in item.childItems():
        yield from _walk(child)


def test_editor_in_inspector_sets_value_through_undoable_command(
    main_window, stage_editor, create_node, qtbot
):
    stage = stage_editor.stage
    node = create_node(stage, "a", type_id=CoreNodes.ACTION)
    add_command = commands.AddNodeComponentCommand(
        node=node, type_id=CoreNodeComponents.VALUE, name="val"
    )
    stage.push_command(add_command)
    component = add_command.result_component
    component.push_value("1+1")
    main_window.inspector.show()
    stage_editor.selection_model.select(
        node.index(), QtCore.QItemSelectionModel.SelectionFlag.Select
    )
    view = main_window.inspector.findChild(NodeComponentsView)
    qtbot.waitUntil(
        lambda: any(
            item.property("maskedText") is not None for item in _walk(view.rootObject())
        ),
        timeout=3000,
    )
    editor = next(
        item
        for item in _walk(view.rootObject())
        if item.property("maskedText") is not None
    )
    assert editor.property("field").property("text") == "2"

    stack_size = stage.undo_stack.count()
    QtCore.QMetaObject.invokeMethod(editor, "requestEdit")
    assert editor.property("field").property("text") == "1+1"
    QtCore.QMetaObject.invokeMethod(
        editor, "finishEdit", QtCore.Q_ARG("QVariant", "3+4")
    )

    assert stage.undo_stack.count() == stack_size + 1
    assert (component.raw_value, component.cached_value) == ("3+4", 7)
    assert editor.property("field").property("text") == "7"
    stage.undo_stack.undo()
    assert component.raw_value == "1+1"


def test_script_file_button_sets_chosen_path(make_editor):
    editor = make_editor(
        CORE_QML_DIR / "ScriptComponentItem.qml", rawValue="pkg.mod:main"
    )
    editor.controller.chosen_file = "/scripts/run.py"
    editor.run("selectScriptFile()")

    (title, filters, start_path) = editor.controller.file_dialogs[0]
    assert start_path == "pkg.mod:main"  # the current value, the controller judges it
    assert "*.py" in filters
    assert editor.controller.calls == [(3, "/scripts/run.py", True)]


def test_script_file_button_cancelled_dialog_changes_nothing(make_editor):
    editor = make_editor(CORE_QML_DIR / "ScriptComponentItem.qml")
    editor.run("selectScriptFile()")
    assert editor.controller.file_dialogs
    assert editor.controller.calls == []


def test_controller_select_file_uses_widget_file_dialog(tmp_path, monkeypatch):
    script = tmp_path / "run.py"
    script.write_text("")
    calls = []

    def fake_dialog(parent, title, start, filters):
        calls.append((title, start, filters))
        return str(script), "Python (*.py)"

    monkeypatch.setattr(QtWidgets.QFileDialog, "getOpenFileName", fake_dialog)
    controller = ComponentsController()

    assert controller.selectFile("Pick", "Python (*.py)", str(script)) == str(script)
    assert controller.selectFile("Pick", "All (*)", str(tmp_path)) == str(script)
    assert controller.selectFile("Pick", "All (*)", "pkg.mod:main") == str(script)
    assert controller.selectFile("Pick", "All (*)", "") == str(script)
    assert [start for _, start, _ in calls] == [str(script), str(tmp_path), "", ""]


def test_controller_select_file_cancelled_returns_empty(monkeypatch):
    monkeypatch.setattr(QtWidgets.QFileDialog, "getOpenFileName", lambda *args: ("", ""))
    assert ComponentsController().selectFile("Pick", "All (*)", "") == ""
