import pytest
from PySide6 import QtCore, QtQml, QtWidgets

from nyx.api.v1 import CoreNodeComponents, CoreNodes, commands
from nyx.editor.controllers.components import ComponentsController
from nyx.editor.views.node_components_view import NodeComponentsView
from nyx.static.enums import ItemSelectionMode

from nyx.static.paths import PACKAGE_ROOT

_KEEP_ALIVE = []
CORE_QML_DIR = PACKAGE_ROOT / "stdlib" / "qml" / "NyxStdlib"


class ControllerStub(QtCore.QObject):
    """Records the calls the editors make on the components controller."""

    def __init__(self):
        super().__init__()
        self.calls = []
        self.file_dialogs = []
        self.datatype_calls = []
        self.chosen_file = ""

    @QtCore.Slot(int, str, bool)
    def setComponentValue(self, row, new_value, raw):
        self.calls.append((row, new_value, raw))

    @QtCore.Slot(int, str)
    def setComponentDatatype(self, row, datatype_id):
        self.datatype_calls.append((row, datatype_id))

    @QtCore.Slot(result="QVariantList")
    def availableDatatypes(self):
        return [
            {"id": "core:object", "name": "Object"},
            {"id": "core:bool", "name": "Boolean"},
        ]

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
    # Shown rendered, as Markdown
    assert editor.field.metaObject().className().startswith("QQuickText")
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


def test_stage_object_path_item_sets_path_without_evaluating(make_editor):
    editor = make_editor(
        CORE_QML_DIR / "StageObjectPathComponentItem.qml",
        rawValue="./target.message",
        displayValue="/stage/target.message",
        isValid=True,
    )
    assert editor.prop("label") == "Object:"
    assert editor.text == "/stage/target.message"  # the live path
    editor.run("requestEdit()")
    assert editor.text == "./target.message"  # what was typed
    editor.run("finishEdit('../other.value')")
    assert editor.controller.calls == [(3, "../other.value", True)]


@pytest.mark.parametrize("is_valid", [True, False])
def test_stage_object_path_item_marks_unresolved_reference(make_editor, is_valid):
    editor = make_editor(
        CORE_QML_DIR / "StageObjectPathComponentItem.qml", isValid=is_valid
    )
    assert (editor.field.property("color").name() == "#b22222") is (not is_valid)


def test_getter_component_path_shows_in_inspector(
    main_window, stage_editor, create_node, qtbot
):
    stage = stage_editor.stage
    target = create_node(stage, "target", type_id=CoreNodes.LOG)
    getter = create_node(stage, "getter", type_id=CoreNodes.GET)
    getter["component"].push_value("./target.message")
    expected = str(target["message"])
    main_window.inspector.show()
    stage_editor.selection_model.select(
        getter.index(), QtCore.QItemSelectionModel.SelectionFlag.Select
    )
    view = main_window.inspector.findChild(NodeComponentsView)

    def reference_editors():
        return [
            item
            for item in _walk(view.rootObject())
            if item.property("maskedText") == expected
        ]

    qtbot.waitUntil(lambda: bool(reference_editors()), timeout=3000)
    editor = reference_editors()[0]
    assert editor.property("label") == "Object:"
    assert editor.property("field").property("color").name() != "#b22222"

    getter["component"].push_value("/stage/missing.message")
    stage_editor.selection_model.clearSelection()
    stage_editor.selection_model.select(
        getter.index(), QtCore.QItemSelectionModel.SelectionFlag.Select
    )
    qtbot.waitUntil(
        lambda: any(
            item.property("maskedText") == "/stage/missing.message"
            and item.property("field").property("color").name() == "#b22222"
            for item in _walk(view.rootObject())
            if item.property("maskedText") is not None and item.property("field")
        ),
        timeout=3000,
    )


def test_reference_in_inspector_updates_without_reselecting(
    main_window, stage_editor, create_node, qtbot
):
    stage = stage_editor.stage
    node = create_node(stage, "node", type_id=CoreNodes.LOG)
    getter = create_node(stage, "getter", type_id=CoreNodes.GET)
    main_window.inspector.show()
    stage_editor.selection_model.select(
        getter.index(), QtCore.QItemSelectionModel.SelectionFlag.Select
    )
    view = main_window.inspector.findChild(NodeComponentsView)

    def reference_editor():
        return next(
            (
                item
                for item in _walk(view.rootObject())
                if item.property("label") == "Object:" and item.property("field")
            ),
            None,
        )

    def is_red(editor):
        return editor.property("field").property("color").name() == "#b22222"

    qtbot.waitUntil(lambda: reference_editor() is not None, timeout=3000)
    editor = reference_editor()
    assert is_red(editor)  # nothing set yet

    def commit(path):
        QtCore.QMetaObject.invokeMethod(editor, "requestEdit")
        QtCore.QMetaObject.invokeMethod(
            editor, "finishEdit", QtCore.Q_ARG("QVariant", path)
        )

    commit("/stage/node")  # a node, not a component
    assert is_red(editor)

    commit("/stage/node.message")
    assert getter["component"].resolve_component() is node["message"]
    assert not is_red(editor)
    assert editor.property("field").property("text") == str(node["message"])

    node.rename("renamed")
    commit("./renamed.message")  # a path through the new name
    assert getter["component"].resolve_component() is node["message"]
    assert editor.property("field").property("text") == str(node["message"])
    assert "renamed.message" in str(node["message"])
    assert not is_red(editor)

    commit("/stage/renamed.nothing")
    assert is_red(editor)


def test_getter_value_in_inspector_updates_when_the_path_changes(
    main_window, stage_editor, create_node, qtbot
):
    stage = stage_editor.stage
    first = create_node(stage, "first", type_id=CoreNodes.LOG)
    second = create_node(stage, "second", type_id=CoreNodes.LOG)
    first["message"].push_value("one")
    second["message"].push_value("two")
    getter = create_node(stage, "getter", type_id=CoreNodes.GET)
    main_window.inspector.show()
    stage_editor.selection_model.select(
        getter.index(), QtCore.QItemSelectionModel.SelectionFlag.Select
    )
    view = main_window.inspector.findChild(NodeComponentsView)

    def editor_labelled(label):
        return next(
            (
                item
                for item in _walk(view.rootObject())
                if item.property("label") == label and item.property("field")
            ),
            None,
        )

    qtbot.waitUntil(
        lambda: editor_labelled("Object:") is not None
        and editor_labelled("Value:") is not None,
        timeout=3000,
    )
    reference, value = editor_labelled("Object:"), editor_labelled("Value:")
    assert value.property("field").property("text") == ""  # nothing to read yet

    def commit(path):
        QtCore.QMetaObject.invokeMethod(reference, "requestEdit")
        QtCore.QMetaObject.invokeMethod(
            reference, "finishEdit", QtCore.Q_ARG("QVariant", path)
        )

    commit("/stage/first.message")
    assert value.property("field").property("text") == "one"  # no reselecting
    commit("/stage/second.message")
    assert value.property("field").property("text") == "two"
    commit("/stage/missing.message")
    assert value.property("field").property("text") == ""


def test_datatype_selector_shows_the_datatype_of_the_component(make_editor):
    editor = make_editor(
        CORE_QML_DIR / "ValueComponentItem.qml", resolvedDatatype="core:bool"
    )

    selector = editor.item.findChild(QtCore.QObject, "datatypeSelector")
    assert selector.property("currentText") == "Boolean"


def test_picking_a_datatype_goes_through_the_controller(make_editor):
    editor = make_editor(
        CORE_QML_DIR / "ValueComponentItem.qml", resolvedDatatype="core:object"
    )

    selector = editor.item.findChild(QtCore.QObject, "datatypeSelector")
    QtCore.QMetaObject.invokeMethod(
        selector,
        "activated",
        QtCore.Qt.ConnectionType.DirectConnection,
        QtCore.Q_ARG(int, 1),
    )
    assert editor.controller.datatype_calls == [(3, "core:bool")]


def test_datatype_selector_is_disabled_when_the_datatype_is_locked(make_editor):
    editor = make_editor(CORE_QML_DIR / "ValueComponentItem.qml", isDatatypeLocked=True)
    selector = editor.item.findChild(QtCore.QObject, "datatypeSelector")
    assert selector.property("enabled") is False


def test_datatype_selector_is_enabled_when_the_datatype_is_not_locked(make_editor):
    editor = make_editor(CORE_QML_DIR / "ValueComponentItem.qml", isDatatypeLocked=False)
    selector = editor.item.findChild(QtCore.QObject, "datatypeSelector")
    assert selector.property("enabled") is True


def test_controller_lists_only_selectable_datatypes(qapp):
    from nyx.editor.controllers.components import ComponentsController

    ids = [entry["id"] for entry in ComponentsController().availableDatatypes()]

    assert "core:bool" in ids
    assert "core:flow" not in ids


def find_edit_button(editor):
    buttons = editor.item.findChildren(QtCore.QObject, "")
    for child in buttons:
        if child.metaObject().className().startswith("EditButton"):
            return child
    return None


@pytest.mark.parametrize(
    "qml_file",
    [
        "ValueComponentItem.qml",
        "StageObjectPathComponentItem.qml",
        "ScriptComponentItem.qml",
        "CommentComponentItem.qml",
    ],
)
def test_core_components_have_an_edit_button_following_the_editing_state(
    make_editor, qml_file
):
    editor = make_editor(CORE_QML_DIR / qml_file)
    button = find_edit_button(editor)

    assert button is not None
    assert button.property("editing") is False
    assert button.property("iconSource").toString().endswith("edit.png")

    editor.run("requestEdit()")
    assert button.property("editing") is True
    assert button.property("iconSource").toString().endswith("check.png")

    editor.run("cancelEdit()")
    assert button.property("iconSource").toString().endswith("edit.png")


def test_edit_button_starts_and_applies_the_edit(value_editor):
    button = find_edit_button(value_editor)

    button.clicked.emit()
    assert value_editor.prop("editing") is True

    value_editor.prop("field").setProperty("text", "5")
    button.clicked.emit()
    assert value_editor.prop("editing") is False
    assert value_editor.controller.calls == [(3, "5", False)]


def test_edit_button_is_hidden_when_the_value_is_not_editable(make_editor):
    editor = make_editor(CORE_QML_DIR / "ValueComponentItem.qml", isEditable=False)

    assert find_edit_button(editor).property("visible") is False


def test_edit_button_is_shown_when_the_value_is_editable(value_editor):
    assert find_edit_button(value_editor).property("visible") is True


def test_tapping_empty_space_in_components_view_deselects_and_closes_palette(
    main_window, stage_editor, create_node, qtbot
):
    stage = stage_editor.stage
    node = create_node(stage, "a", type_id=CoreNodes.ACTION)
    stage.push_command(
        commands.AddNodeComponentCommand(
            node=node, type_id=CoreNodeComponents.VALUE, name="val"
        )
    )
    main_window.inspector.show()
    stage_editor.selection_model.select(
        node.index(), QtCore.QItemSelectionModel.SelectionFlag.Select
    )
    view = main_window.inspector.findChild(NodeComponentsView)
    qtbot.waitUntil(lambda: view.rootObject() is not None, timeout=3000)
    root = view.rootObject()
    controller = view._controller
    qtbot.waitUntil(lambda: controller.components_model is not None, timeout=3000)

    def tap(x, y):
        QtCore.QMetaObject.invokeMethod(
            root,
            "handleTapInList",
            QtCore.Q_ARG("QVariant", x),
            QtCore.Q_ARG("QVariant", y),
        )

    controller.selectRow(0, ItemSelectionMode.REPLACE)
    assert controller.selection_model.hasSelection()
    palette = root.findChild(QtCore.QObject, "palettePopup")
    QtCore.QMetaObject.invokeMethod(palette, "open")

    # On the component: nothing happens
    list_view = root.findChild(QtCore.QObject, "componentsListView")
    qtbot.waitUntil(lambda: list_view.property("count") > 0, timeout=3000)
    delegate = next(
        item
        for item in list_view.property("contentItem").childItems()
        if item.property("showExpanded") is not None
    )
    on_delegate = delegate.mapToItem(list_view, QtCore.QPointF(20, 5))
    tap(on_delegate.x(), on_delegate.y())
    assert controller.selection_model.hasSelection()

    # Far below the only component
    tap(20, 5000)
    assert not controller.selection_model.hasSelection()
    assert palette.property("opened") is False


def test_clicking_empty_space_in_components_view_deselects(
    main_window, stage_editor, create_node, qtbot
):
    from PySide6 import QtTest

    stage = stage_editor.stage
    node = create_node(stage, "a", type_id=CoreNodes.ACTION)
    stage.push_command(
        commands.AddNodeComponentCommand(
            node=node, type_id=CoreNodeComponents.VALUE, name="val"
        )
    )
    main_window.inspector.show()
    stage_editor.selection_model.select(
        node.index(), QtCore.QItemSelectionModel.SelectionFlag.Select
    )
    view = main_window.inspector.findChild(NodeComponentsView)
    qtbot.waitUntil(lambda: view.rootObject() is not None, timeout=3000)
    root = view.rootObject()
    controller = view._controller
    list_view = root.findChild(QtCore.QObject, "componentsListView")
    qtbot.waitUntil(lambda: list_view.property("count") > 0, timeout=3000)
    palette = root.findChild(QtCore.QObject, "palettePopup")

    controller.selectRow(0, ItemSelectionMode.REPLACE)
    QtCore.QMetaObject.invokeMethod(palette, "open")
    assert controller.selection_model.hasSelection()

    content_height = list_view.property("contentHeight")
    # Just below the components, above the palette popup that covers the rest
    popup_top = palette.property("y")
    assert popup_top > content_height + 10
    empty = list_view.mapToItem(root, QtCore.QPointF(30, content_height + 5))
    QtTest.QTest.mouseClick(
        view,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(int(empty.x()), int(empty.y())),
    )

    qtbot.waitUntil(lambda: not controller.selection_model.hasSelection(), timeout=2000)
    assert palette.property("opened") is False


def test_component_items_have_the_description_tooltip(
    main_window, stage_editor, create_node, qtbot
):
    stage = stage_editor.stage
    node = create_node(stage, "a", type_id=CoreNodes.BRANCH)
    main_window.inspector.show()
    stage_editor.selection_model.select(
        node.index(), QtCore.QItemSelectionModel.SelectionFlag.Select
    )
    view = main_window.inspector.findChild(NodeComponentsView)
    qtbot.waitUntil(lambda: view.rootObject() is not None, timeout=3000)
    root = view.rootObject()
    list_view = root.findChild(QtCore.QObject, "componentsListView")
    qtbot.waitUntil(lambda: list_view.property("count") > 0, timeout=3000)

    delegates = [
        item
        for item in list_view.property("contentItem").childItems()
        if item.property("showExpanded") is not None
    ]
    tooltips = [
        child
        for delegate in delegates
        for child in delegate.findChildren(QtCore.QObject)
        if child.metaObject().className().startswith("DescriptionToolTip")
    ]
    assert len(tooltips) == len(delegates) > 0
    texts = {tooltip.property("text") for tooltip in tooltips}
    assert "Flow that continues when the condition is true." in texts
    assert any(text.startswith("Value that chooses the output") for text in texts)


def _comment_walk(item):
    yield item
    for child in item.childItems():
        yield from _comment_walk(child)


def _text_format(editor):
    value, failed = QtQml.QQmlExpression(
        editor.context, editor.field, "textFormat + 0"
    ).evaluate()
    assert not failed
    return value


def test_comment_is_shown_as_markdown(make_editor):
    editor = make_editor(
        CORE_QML_DIR / "CommentComponentItem.qml", rawValue="**a**", displayValue="**a**"
    )

    assert _text_format(editor) == QtCore.Qt.TextFormat.MarkdownText.value
    assert editor.field.property("text") == "**a**"


def test_empty_comment_shows_a_hint_instead_of_markdown(make_editor):
    editor = make_editor(
        CORE_QML_DIR / "CommentComponentItem.qml", rawValue="", displayValue=""
    )

    assert editor.field.property("text") == "Empty comment"
    assert _text_format(editor) == QtCore.Qt.TextFormat.PlainText.value


def test_comment_editor_has_a_tall_text_area_and_the_three_buttons(make_editor):
    editor = make_editor(
        CORE_QML_DIR / "CommentComponentItem.qml", rawValue="hello", displayValue="hello"
    )
    editor.run("requestEdit()")

    items = list(_comment_walk(editor.field))
    area = next(
        item
        for item in items
        if item.property("placeholderText") == "Write a comment..."
    )
    assert area.property("text") == "hello"
    assert area.property("height") >= 100
    assert any(
        item.metaObject().className().startswith("EditActionButtons") for item in items
    )
    assert editor.field.property("text") == "hello"


def test_comment_editor_clear_and_apply(make_editor):
    editor = make_editor(
        CORE_QML_DIR / "CommentComponentItem.qml", rawValue="hello", displayValue="hello"
    )
    editor.run("requestEdit()")
    buttons = next(
        item
        for item in _comment_walk(editor.field)
        if item.metaObject().className().startswith("EditActionButtons")
    )

    buttons.clearRequested.emit()
    assert editor.field.property("text") == ""
    assert editor.prop("editing") is True

    buttons.applyRequested.emit()
    assert editor.prop("editing") is False
    assert editor.controller.calls == [(3, "", True)]


def test_comment_editor_cancel_changes_nothing(make_editor):
    editor = make_editor(
        CORE_QML_DIR / "CommentComponentItem.qml", rawValue="hello", displayValue="hello"
    )
    editor.run("requestEdit()")
    buttons = next(
        item
        for item in _comment_walk(editor.field)
        if item.metaObject().className().startswith("EditActionButtons")
    )
    editor.field.setProperty("text", "typed")

    buttons.cancelRequested.emit()

    assert editor.prop("editing") is False
    assert editor.controller.calls == []


def test_comment_edit_button_gives_way_to_the_editor_buttons(make_editor):
    editor = make_editor(
        CORE_QML_DIR / "CommentComponentItem.qml", rawValue="hello", displayValue="hello"
    )
    button = find_edit_button(editor)

    assert button.property("visible") is True
    editor.run("requestEdit()")
    assert button.property("visible") is False
    editor.run("cancelEdit()")
    assert button.property("visible") is True
