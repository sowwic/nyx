import pytest

from nyx.api.v1 import (
    CoreNodeComponents,
    CoreNodes,
    NodeComponent,
    NoteFormat,
    Stage,
    commands,
    exceptions,
)


@pytest.fixture
def stage_and_component():
    stage = Stage()
    node_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.ACTION)
    stage.push_command(node_command)
    component_command = commands.AddNodeComponentCommand(
        node=node_command.result_node, type_id=CoreNodeComponents.VALUE, name="val"
    )
    stage.push_command(component_command)
    return stage, component_command.result_component


def test_component_has_no_note_by_default(stage_and_component):
    _stage, component = stage_and_component

    assert component.note == ""
    assert component.note_format is NoteFormat.PLAIN


def test_note_and_format_are_roles(stage_and_component):
    _stage, component = stage_and_component
    component.note = "# Title"
    component.note_format = NoteFormat.MARKDOWN

    assert component.data(NodeComponent.Roles.NOTE) == "# Title"
    assert component.data(NodeComponent.Roles.NOTE_FORMAT) == "markdown"
    model = component.model()
    assert model.roleNames()[NodeComponent.Roles.NOTE] == b"note"
    assert model.roleNames()[NodeComponent.Roles.NOTE_FORMAT] == b"noteFormat"
    assert model.data(component.index(), NodeComponent.Roles.NOTE) == "# Title"


def test_note_format_rejects_unknown_formats(stage_and_component):
    _stage, component = stage_and_component

    with pytest.raises(ValueError):
        component.note_format = "rtf"


def test_note_is_serialized_as_a_dict(stage_and_component):
    _stage, component = stage_and_component
    component.note = "<b>hi</b>"
    component.note_format = NoteFormat.HTML

    assert component.serialize()["note"] == {"text": "<b>hi</b>", "format": "html"}


def test_note_survives_a_serialization_round_trip(stage_and_component):
    stage, component = stage_and_component
    component.note = "remember"
    component.note_format = NoteFormat.MARKDOWN
    serialized = component.node.serialize()

    other = Stage()
    from nyx.api.v1 import RestoreUuidOption
    from nyx.core.node import Node

    restored = Node.deserialize(
        serialized,
        parent_node=other.root_node,
        restore_uuid=RestoreUuidOption.ATTEMPT_RESTORE,
    )

    assert restored["val"].note == "remember"
    assert restored["val"].note_format is NoteFormat.MARKDOWN


def test_old_files_without_a_note_load_with_an_empty_one(stage_and_component):
    _stage, component = stage_and_component
    serialized = component.node.serialize()
    for data in serialized["components"]:
        data.pop("note", None)

    other = Stage()
    from nyx.core.node import Node

    restored = Node.deserialize(serialized, parent_node=other.root_node)

    assert restored["val"].note == ""
    assert restored["val"].note_format is NoteFormat.PLAIN


def test_set_note_command_sets_and_undoes(stage_and_component):
    stage, component = stage_and_component
    command = commands.SetNodeComponentNoteCommand(
        stage=stage,
        node_component=component,
        text="a note",
        note_format=NoteFormat.MARKDOWN,
    )
    stage.push_command(command)

    assert component.note == "a note"
    assert component.note_format is NoteFormat.MARKDOWN

    stage.undo_stack.undo()
    assert component.note == ""
    assert component.note_format is NoteFormat.PLAIN

    stage.undo_stack.redo()
    assert component.note == "a note"


def test_set_note_command_keeps_the_format_if_omitted(stage_and_component):
    stage, component = stage_and_component
    component.note_format = NoteFormat.HTML
    stage.push_command(
        commands.SetNodeComponentNoteCommand(
            stage=stage, node_component=component, text="x"
        )
    )

    assert component.note_format is NoteFormat.HTML


def test_set_note_command_rejects_unknown_format(stage_and_component):
    stage, component = stage_and_component
    command = commands.SetNodeComponentNoteCommand(
        stage=stage, node_component=component, text="x", note_format="rtf"
    )

    with pytest.raises(exceptions.NyxCommandValidationError):
        stage.push_command(command)
    assert component.note == ""
