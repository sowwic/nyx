import pytest
from PySide6 import QtCore, QtQml

from nyx.api.v1 import CoreNodeComponents, CoreNodes, NoteFormat, commands
from nyx.editor.views.node_components_view import NodeComponentsView
from nyx.static.paths import PACKAGE_ROOT

NOTE_QML = (
    PACKAGE_ROOT / "editor" / "qml" / "NyxEditor" / "ComponentsView"
    / "NodeComponentNoteItem.qml"
)  # fmt: skip
_KEEP_ALIVE = []


def invoke(item, name, *args):
    return QtCore.QMetaObject.invokeMethod(
        item,
        name,
        QtCore.Qt.ConnectionType.DirectConnection,
        *[QtCore.Q_ARG("QVariant", arg) for arg in args],
    )


def walk(item):
    yield item
    for child in item.childItems():
        yield from walk(child)


@pytest.fixture
def note_item(qapp):
    component = QtQml.QQmlComponent(
        qapp.qml_engine, QtCore.QUrl.fromLocalFile(str(NOTE_QML))
    )
    item = component.create()
    assert item is not None, component.errorString()
    _KEEP_ALIVE.append(component)
    item.setProperty(
        "noteFormats",
        [
            {"id": str(note_format), "name": note_format.name.title()}
            for note_format in NoteFormat
        ],
    )
    committed = []
    item.noteCommitted.connect(lambda text, fmt: committed.append((text, fmt)))
    item.committed = committed
    yield item
    item.deleteLater()


def test_note_item_without_a_note_has_none(note_item):
    assert note_item.property("hasNote") is False
    assert note_item.property("editing") is False


@pytest.mark.parametrize(
    "note_format, expected",
    [
        ("plain", QtCore.Qt.TextFormat.PlainText.value),
        ("markdown", QtCore.Qt.TextFormat.MarkdownText.value),
        ("html", QtCore.Qt.TextFormat.RichText.value),
        ("unknown", QtCore.Qt.TextFormat.PlainText.value),
    ],
)
def test_each_format_is_rendered_with_its_text_format(
    qapp, note_item, note_format, expected
):
    note_item.setProperty("note", "text")
    note_item.setProperty("noteFormat", note_format)
    rendered = next(
        item for item in walk(note_item) if item.property("linkColor") is not None
    )
    context = QtQml.QQmlContext(qapp.qml_engine.rootContext())
    value, failed = QtQml.QQmlExpression(context, rendered, "textFormat + 0").evaluate()

    assert not failed
    assert value == expected


def test_editing_starts_from_the_current_note_and_format(note_item):
    note_item.setProperty("note", "hello")
    note_item.setProperty("noteFormat", "markdown")

    invoke(note_item, "beginEdit")

    assert note_item.property("editing") is True
    editor = next(
        item
        for item in walk(note_item)
        if item.property("placeholderText") == "Write a note..."
    )
    assert editor.property("text") == "hello"


def test_commit_reports_the_text_and_format(note_item):
    note_item.setProperty("note", "hello")
    invoke(note_item, "beginEdit")
    editor = next(
        item
        for item in walk(note_item)
        if item.property("placeholderText") == "Write a note..."
    )
    editor.setProperty("text", "changed")

    invoke(note_item, "commitEdit")

    assert note_item.property("editing") is False
    assert note_item.committed == [("changed", "plain")]


def test_cancel_reports_nothing(note_item):
    invoke(note_item, "beginEdit")
    invoke(note_item, "cancelEdit")

    assert note_item.property("editing") is False
    assert note_item.committed == []


def test_commit_without_editing_does_nothing(note_item):
    invoke(note_item, "commitEdit")

    assert note_item.committed == []


@pytest.fixture
def inspector_delegate(main_window, stage_editor, create_node, qtbot):
    stage = stage_editor.stage
    node = create_node(stage, "a", type_id=CoreNodes.ACTION)
    command = commands.AddNodeComponentCommand(
        node=node, type_id=CoreNodeComponents.VALUE, name="val"
    )
    stage.push_command(command)
    component = command.result_component
    main_window.inspector.show()
    stage_editor.selection_model.select(
        node.index(), QtCore.QItemSelectionModel.SelectionFlag.Select
    )
    view = main_window.inspector.findChild(NodeComponentsView)
    qtbot.waitUntil(lambda: view.rootObject() is not None, timeout=3000)
    list_view = view.rootObject().findChild(QtCore.QObject, "componentsListView")
    qtbot.waitUntil(lambda: list_view.property("count") > 1, timeout=3000)

    def find_delegate():
        for item in list_view.property("contentItem").childItems():
            if (
                item.property("name") == "val"
                and item.property("showExpanded") is not None
            ):
                return item
        return None

    qtbot.waitUntil(lambda: find_delegate() is not None, timeout=3000)

    def frame():
        delegate = find_delegate()
        return next(
            child for child in walk(delegate) if child.objectName() == "noteFrame"
        )

    return stage, component, find_delegate, frame


def test_note_frame_is_hidden_while_there_is_no_note(inspector_delegate):
    _stage, _component, _delegate, frame = inspector_delegate

    assert frame().property("visible") is False


def test_note_frame_shows_a_note_and_hides_when_it_is_removed(inspector_delegate):
    stage, component, _delegate, frame = inspector_delegate

    stage.push_command(
        commands.SetNodeComponentNoteCommand(
            stage=stage, node_component=component, text="remember this"
        )
    )
    assert frame().property("visible") is True

    stage.push_command(
        commands.SetNodeComponentNoteCommand(
            stage=stage, node_component=component, text=""
        )
    )
    assert frame().property("visible") is False


def test_note_frame_hides_while_the_component_is_dragged(inspector_delegate):
    stage, component, delegate, frame = inspector_delegate
    stage.push_command(
        commands.SetNodeComponentNoteCommand(
            stage=stage, node_component=component, text="x"
        )
    )
    assert frame().property("visible") is True

    delegate().setProperty("isDragging", True)
    assert frame().property("visible") is False


def test_edit_note_menu_option_opens_the_editor_of_a_hidden_note(inspector_delegate):
    stage, component, delegate, frame = inspector_delegate
    assert frame().property("visible") is False

    invoke(delegate(), "startNoteEdit")

    assert frame().property("visible") is True
    note_item = next(
        child for child in walk(frame()) if child.objectName() == "noteItem"
    )
    assert note_item.property("editing") is True


def test_committing_the_edit_pushes_an_undoable_command(inspector_delegate):
    stage, component, delegate, frame = inspector_delegate
    invoke(delegate(), "startNoteEdit")
    note_item = next(
        child for child in walk(frame()) if child.objectName() == "noteItem"
    )
    editor = next(
        item
        for item in walk(note_item)
        if item.property("placeholderText") == "Write a note..."
    )
    editor.setProperty("text", "# done")
    stack_size = stage.undo_stack.count()

    invoke(note_item, "commitEdit")

    assert stage.undo_stack.count() == stack_size + 1
    assert component.note == "# done"
    stage.undo_stack.undo()
    assert component.note == ""


def test_edit_note_menu_item_is_above_help():
    source = (
        PACKAGE_ROOT / "editor" / "qml" / "NyxEditor" / "ComponentsView"
        / "NodeComponentDelegate.qml"
    ).read_text()  # fmt: skip

    assert 'text: "Edit Note"' in source
    assert source.index('text: "Edit Note"') < source.index('text: "Help"')


def test_clear_empties_the_editor_but_keeps_editing(note_item):
    note_item.setProperty("note", "hello")
    invoke(note_item, "beginEdit")
    editor = next(
        item
        for item in walk(note_item)
        if item.property("placeholderText") == "Write a note..."
    )
    assert editor.property("text") == "hello"

    invoke(note_item, "clearEditor")

    assert editor.property("text") == ""
    assert note_item.property("editing") is True
    assert note_item.committed == []

    # Applying the empty text removes the note
    invoke(note_item, "commitEdit")
    assert note_item.committed == [("", "plain")]


def test_editor_is_taller_than_a_single_line(note_item):
    note_item.setProperty("width", 300)
    invoke(note_item, "beginEdit")
    editor = next(
        item
        for item in walk(note_item)
        if item.property("placeholderText") == "Write a note..."
    )

    assert editor.property("height") >= 100


def test_note_frame_state_is_kept_in_the_model(inspector_delegate):
    _stage, component, delegate, frame = inspector_delegate
    assert component.is_note_expanded is True

    component.is_note_expanded = False
    assert frame().property("isExpanded") is False

    component.is_note_expanded = True
    assert frame().property("isExpanded") is True


def test_toggling_the_note_frame_writes_back_to_the_model(inspector_delegate):
    stage, component, delegate, frame = inspector_delegate
    stage.push_command(
        commands.SetNodeComponentNoteCommand(
            stage=stage, node_component=component, text="x"
        )
    )

    invoke(frame(), "toggleExpandedState")
    assert component.is_note_expanded is False

    # The binding still follows the model after a toggle by the user
    component.is_note_expanded = True
    assert frame().property("isExpanded") is True


def test_edit_note_opens_a_collapsed_frame(inspector_delegate):
    _stage, component, delegate, frame = inspector_delegate
    component.is_note_expanded = False

    invoke(delegate(), "startNoteEdit")

    assert component.is_note_expanded is True
    assert frame().property("isExpanded") is True


def test_editor_fits_a_narrow_frame(note_item):
    invoke(note_item, "beginEdit")

    # The frame of the inspector is about 300px wide, minus its padding
    note_item.setProperty("width", 270)
    for item in walk(note_item):
        if item.property("visible") and item.width() > 0:
            right = item.mapToItem(note_item, QtCore.QPointF(item.width(), 0)).x()
            assert right <= 270.5, item
