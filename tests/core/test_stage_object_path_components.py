import pathlib

import pytest
from PySide6 import QtCore

from nyx.api.v1 import (
    CoreNodeComponents,
    CoreNodes,
    NodeComponent,
    NodeComponentFlag,
    Stage,
    commands,
    exceptions,
)
from nyx.stdlib.node_components.object_path import StageObjectPathComponent


def create(stage, type_id=CoreNodes.ACTION, name=None, parent=None):
    command = commands.CreateNodeCommand(
        stage=stage, type_id=type_id, name=name, parent_node=parent
    )
    stage.push_command(command)
    return command.result_node


def paste(stage, nodes, parent=None):
    command = commands.PasteNodesCommand(
        stage=stage,
        serialize_nodes=[node.serialize() for node in nodes],
        position=QtCore.QPointF(0, 0),
        parent_node=parent,
    )
    stage.push_command(command)
    return command.pasted_nodes


def of_type(nodes, type_id):
    return next(node for node in nodes if node.get_type_id() == type_id)


@pytest.fixture
def getter_and_target():
    """Stage with a getter pointing at the message of a log node."""
    stage = Stage()
    target = create(stage, CoreNodes.LOG, name="target")
    getter = create(stage, CoreNodes.GET, name="getter")
    getter["component"].push_value("/stage/target.message")
    return stage, getter, target


# ======== Component ========= #


def test_object_path_has_its_own_type():
    component = StageObjectPathComponent()
    assert component.get_type_id() == CoreNodeComponents.STAGE_OBJECT_PATH
    assert component.is_editable
    assert NodeComponentFlag.STATIC in component.component_flags
    assert not component.is_valid  # nothing to point at while detached


def test_getter_and_setter_only_accept_component_paths(getter_and_target):
    stage, getter, _target = getter_and_target
    setter = create(stage, CoreNodes.SET, name="setter")
    for owner in (getter, setter):
        assert owner["component"].target_types == (NodeComponent,)


def test_full_component_path_resolves_to_component(getter_and_target):
    _stage, getter, target = getter_and_target
    object_path = getter["component"]

    assert object_path.target_component is target["message"]
    assert object_path.resolve_component() is target["message"]
    assert object_path.target_node is target
    assert object_path.target_uuid == target["message"].uuid
    assert object_path.pull_value() == "/stage/target.message"
    assert object_path.is_valid


@pytest.mark.parametrize(
    "text", ["target.message", "./target.message", "../stage/target.message"]
)
def test_relative_component_path_resolves_against_scope_of_owner(
    getter_and_target, text
):
    _stage, getter, target = getter_and_target
    getter["component"].push_value(text)
    assert getter["component"].resolve_component() is target["message"]
    assert getter["component"].pull_value() == "/stage/target.message"


def test_relative_path_in_child_scope():
    stage = Stage()
    group = create(stage, name="group")
    target = create(stage, CoreNodes.LOG, name="target", parent=group)
    outer = create(stage, CoreNodes.LOG, name="outer")
    getter = create(stage, CoreNodes.GET, name="getter", parent=group)

    getter["component"].push_value("./target.message")
    assert getter["component"].resolve_component() is target["message"]
    getter["component"].push_value("../outer.message")
    assert getter["component"].resolve_component() is outer["message"]


def test_object_path_follows_renamed_node_and_component(getter_and_target):
    _stage, getter, target = getter_and_target
    object_path = getter["component"]
    message = target["message"]

    target.rename("renamed")
    message.name = "text"

    assert object_path.resolve_component() is message
    assert object_path.pull_value() == "/stage/renamed.text"


@pytest.mark.parametrize(
    "text",
    [
        None,
        "",
        "/stage/target",  # a node, not a component
        "/stage/target.nothing",  # no such component
        "/stage/nothing.message",  # no such node
    ],
)
def test_wrong_or_missing_target_is_unresolved(getter_and_target, text):
    _stage, getter, _target = getter_and_target
    object_path = getter["component"]
    object_path.push_value(text)

    assert object_path.target_component is None
    assert object_path.target_node is None
    assert not object_path.is_valid
    with pytest.raises(exceptions.StageObjectQueryError):
        object_path.resolve_component()


def test_suffix_decides_between_node_and_component(getter_and_target):
    stage, _getter, target = getter_and_target
    owner = create(stage, name="owner")
    add_command = commands.AddNodeComponentCommand(
        node=owner, type_id=CoreNodeComponents.STAGE_OBJECT_PATH, name="ref"
    )
    stage.push_command(add_command)
    object_path = add_command.result_component
    message = target["message"]

    object_path.push_value("/stage/target")
    assert object_path.target is target
    assert object_path.resolve_node() is target
    assert object_path.target_component is None
    with pytest.raises(exceptions.StageObjectQueryError):
        object_path.resolve_component()

    object_path.push_value("/stage/target.message")
    assert object_path.target is message
    assert object_path.resolve_component() is message
    assert object_path.target_node is target  # the node owning the component
    with pytest.raises(exceptions.StageObjectQueryError):
        object_path.resolve_node()

    object_path.push_value("./target.message")  # relative, same rule
    assert object_path.target is message
    assert object_path.is_valid


def test_node_path_is_unresolved_when_only_components_are_accepted(getter_and_target):
    _stage, getter, target = getter_and_target
    object_path = getter["component"]

    object_path.push_value("/stage/target")
    assert object_path.target is None
    assert not object_path.is_valid
    assert object_path.pull_value() == "/stage/target"  # shown as typed

    object_path.push_value("/stage/target.message")
    assert object_path.is_valid
    assert object_path.resolve_component() is target["message"]


def test_linked_object_path_provides_the_path():
    stage = Stage()
    target = create(stage, CoreNodes.LOG, name="target")
    setter = create(stage, CoreNodes.SET, name="setter")
    source_node = create(stage, name="source")
    add_command = commands.AddNodeComponentCommand(
        node=source_node, type_id=CoreNodeComponents.STAGE_OBJECT_PATH, name="path"
    )
    stage.push_command(add_command)
    source = add_command.result_component
    source.readable = True
    source.push_value("/stage/target.message")

    stage.push_command(
        commands.LinkNodeComponentsCommand(
            stage=stage, source=source, target=setter["component"]
        )
    )
    assert setter["component"].resolve_component() is target["message"]
    source.push_value("/stage/target.nothing")
    assert not setter["component"].is_valid


def test_plain_value_can_be_linked_into_the_component_field():
    stage = Stage()
    setter = create(stage, CoreNodes.SET, name="setter")
    source_node = create(stage, name="source")
    add_command = commands.AddNodeComponentCommand(
        node=source_node, type_id=CoreNodeComponents.VALUE, name="path"
    )
    stage.push_command(add_command)
    add_command.result_component.readable = True

    # A plain value is a wildcard datatype, so it is accepted.
    stage.push_command(
        commands.LinkNodeComponentsCommand(
            stage=stage,
            source=add_command.result_component,
            target=setter["component"],
        )
    )
    assert len(setter["component"].input_links) == 1


def test_object_path_survives_delete_and_undo_of_component_and_node(getter_and_target):
    stage, getter, target = getter_and_target
    object_path = getter["component"]

    stage.push_command(commands.DeleteNodeCommand(stage=stage, nodes=[target]))
    assert not object_path.is_valid
    stage.undo_stack.undo()
    assert object_path.is_valid
    assert object_path.resolve_component().node.name == "target"


def test_set_value_command_undo_redo(getter_and_target):
    stage, getter, target = getter_and_target
    other = create(stage, CoreNodes.LOG, name="other")
    object_path = getter["component"]

    stage.push_command(
        commands.SetNodeComponentValueCommand(
            stage=stage,
            node_component=object_path,
            value="/stage/other.message",
            raw=True,
        )
    )
    assert object_path.resolve_component() is other["message"]
    stage.undo_stack.undo()
    assert object_path.resolve_component() is target["message"]


# ======== Getter and setter ========= #


def test_getter_and_setter_use_a_single_component_path():
    stage = Stage()
    log = create(stage, CoreNodes.LOG, name="log")
    log["message"].push_value("hello")
    getter = create(stage, CoreNodes.GET, name="getter")
    getter["component"].push_value("log.message")
    assert getter["value"].pull_value() == "hello"

    setter = create(stage, CoreNodes.SET, name="setter")
    setter["component"].push_value("./log.message")
    setter["value"].push_value("changed")
    setter.execute()
    assert log["message"].cached_value == "changed"
    assert getter["value"].pull_value() == "changed"


# ======== Serialization ========= #


def test_serialized_value_has_uuid_and_scope_relative_path(getter_and_target):
    _stage, getter, target = getter_and_target
    assert getter["component"].serialize_value() == {
        "target_uuid": str(target["message"].uuid),
        "path": "target.message",
    }


def test_export_import_roundtrip(output_dir: pathlib.Path, getter_and_target):
    stage, getter, target = getter_and_target
    export_path = output_dir / f"roundtrip{Stage.FILE_EXTENSION}"
    stage.export_json(export_path)

    other_stage = Stage()
    other_stage.import_json(export_path)

    assert stage.root_node.serialize() == other_stage.root_node.serialize()
    new_getter = other_stage.get_object(getter.path)
    assert new_getter["component"].resolve_component().path == target["message"].path


# ======== Pasting and importing ========= #


@pytest.mark.parametrize("getter_first", [True, False])
def test_pasting_group_in_same_scope_points_copies_at_each_other(
    getter_and_target, getter_first
):
    stage, getter, target = getter_and_target
    nodes = [getter, target] if getter_first else [target, getter]

    pasted = paste(stage, nodes)
    new_getter = of_type(pasted, CoreNodes.GET)
    new_target = of_type(pasted, CoreNodes.LOG)

    assert new_target is not target
    assert new_getter["component"].resolve_component() is new_target["message"]
    assert getter["component"].resolve_component() is target["message"]


def test_pasting_only_the_getter_keeps_pointing_at_the_original(getter_and_target):
    stage, getter, target = getter_and_target
    (new_getter,) = paste(stage, [getter])
    assert new_getter["component"].resolve_component() is target["message"]


def test_pasting_group_into_another_stage_points_at_the_copies(getter_and_target):
    _stage, getter, target = getter_and_target
    other_stage = Stage()

    pasted = paste(other_stage, [getter, target])
    new_getter = of_type(pasted, CoreNodes.GET)
    new_target = of_type(pasted, CoreNodes.LOG)

    assert new_getter["component"].resolve_component() is new_target["message"]
    assert new_getter.stage is other_stage


def test_pasting_group_into_a_child_scope_follows_the_group(getter_and_target):
    stage, getter, target = getter_and_target
    destination = create(stage, name="destination")
    getter["component"].push_value("./target.message")

    pasted = paste(stage, [getter, target], parent=destination)
    new_getter = of_type(pasted, CoreNodes.GET)
    new_target = of_type(pasted, CoreNodes.LOG)

    assert new_target.parent() is destination
    assert new_getter["component"].resolve_component() is new_target["message"]
    assert new_getter["component"].pull_value() == "/stage/destination/target.message"


def test_external_target_in_another_stage_falls_back_to_relative_path(
    getter_and_target,
):
    _stage, getter, _target = getter_and_target
    other_stage = Stage()
    local_target = create(other_stage, CoreNodes.LOG, name="target")

    (new_getter,) = paste(other_stage, [getter])
    assert new_getter["component"].resolve_component() is local_target["message"]


def test_external_target_missing_in_another_stage_is_unresolved(getter_and_target):
    _stage, getter, _target = getter_and_target
    other_stage = Stage()

    (new_getter,) = paste(other_stage, [getter])
    assert not new_getter["component"].is_valid
    create(other_stage, CoreNodes.LOG, name="target")  # shows up where it looks
    assert new_getter["component"].is_valid


def test_paste_undo_redo_keeps_object_paths(getter_and_target):
    stage, getter, target = getter_and_target
    command = commands.PasteNodesCommand(
        stage=stage,
        serialize_nodes=[getter.serialize(), target.serialize()],
        position=QtCore.QPointF(0, 0),
    )
    stage.push_command(command)
    stage.undo_stack.undo()
    stage.undo_stack.redo()

    new_getter = of_type(command.pasted_nodes, CoreNodes.GET)
    new_target = of_type(command.pasted_nodes, CoreNodes.LOG)
    assert new_getter["component"].resolve_component() is new_target["message"]


# ======== Notifying views ========= #


def test_views_get_the_new_display_and_validity(getter_and_target):
    stage, getter, _target = getter_and_target
    create(stage, CoreNodes.LOG, name="other")
    object_path = getter["component"]
    model, index = object_path.model(), object_path.index()
    changes = []

    def on_changed(top_left, _bottom_right, roles):
        if top_left == index:
            changes.append(
                (
                    set(roles),
                    index.data(object_path.Roles.DISPLAY_VALUE),
                    index.data(object_path.Roles.IS_VALID),
                )
            )

    model.dataChanged.connect(on_changed)

    object_path.push_value("/stage/other.message")
    display_changes = [c for c in changes if object_path.Roles.DISPLAY_VALUE in c[0]]
    other_message = stage.get_object("/stage/other.message")
    old_message = stage.get_object("/stage/target.message")
    assert display_changes[-1][1] == str(other_message)
    assert all(c[1] != str(old_message) for c in display_changes)

    changes.clear()
    object_path.push_value("/stage/other.nothing")
    validity_changes = [c for c in changes if object_path.Roles.IS_VALID in c[0]]
    assert validity_changes[-1][2] is False


# ======== Older files ========= #


def test_getter_saved_with_node_path_and_cpnt_name_still_loads():
    """Older getters had a node path and a component name instead of a component path."""
    from copy import deepcopy
    from uuid import uuid4

    from nyx.api.v1 import NodeComponent

    stage = Stage()
    getter = create(stage, CoreNodes.GET, name="getter")
    serialized = getter.serialize()
    template = next(c for c in serialized["components"] if c["name"] == "value")
    for name, value in (("node_path", "/stage/target"), ("cpnt_name", "message")):
        old_component = deepcopy(template)
        old_component["name"] = name
        old_component["value"] = value
        old_component[NodeComponent.UUID_KEY] = str(uuid4())
        serialized["components"].append(old_component)

    class Serialized:
        def serialize(self):
            return serialized

    (loaded,) = paste(Stage(), [Serialized()])

    names = [component.name for component in loaded.components_model.list_components()]
    assert names == ["component", "value", "node_path", "cpnt_name"]
    # The old split values are kept as they were, but nothing reads them anymore.
    assert loaded["node_path"].raw_value == "/stage/target"
    assert not loaded["component"].is_valid


# ======== Display ========= #


def test_display_shows_the_target_and_cached_value_is_the_path(getter_and_target):
    _stage, getter, target = getter_and_target
    object_path = getter["component"]

    assert object_path.get_display_value() == str(target["message"])
    assert object_path.get_display_value() == "ValueComponent (/stage/target.message)"
    index = object_path.index()
    assert index.data(object_path.Roles.DISPLAY_VALUE) == str(target["message"])
    # Consumers still get something they can use as a path.
    assert object_path.pull_value() == "/stage/target.message"
    assert object_path.cached_value == "/stage/target.message"


def test_display_follows_renames(getter_and_target):
    _stage, getter, target = getter_and_target
    target.rename("renamed")
    assert getter["component"].get_display_value() == str(target["message"])
    assert "renamed.message" in getter["component"].get_display_value()


@pytest.mark.parametrize(
    "text, shown", [("/stage/nothing.message", "/stage/nothing.message"), (None, "")]
)
def test_display_shows_the_text_when_there_is_no_target(getter_and_target, text, shown):
    _stage, getter, _target = getter_and_target
    getter["component"].push_value(text)
    assert getter["component"].get_display_value() == shown
    assert not getter["component"].is_valid


def test_object_path_component_uses_the_object_path_datatype():
    from nyx.api.v1 import CoreDatatypes, GraphicsPlugShape

    stage = Stage()
    command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.GET)
    stage.push_command(command)
    object_path = command.result_node["component"]

    assert object_path.datatype_id == CoreDatatypes.STAGE_OBJECT_PATH
    assert object_path.get_plug_shape() is GraphicsPlugShape.SQUARE


def test_name_text_is_the_last_part_of_the_path():
    stage = Stage()
    target_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.LOG, name="target"
    )
    stage.push_command(target_command)
    getter_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.GET)
    stage.push_command(getter_command)
    object_path = getter_command.result_node["component"]

    assert object_path.current_name_text() == ""

    object_path.push_value("/stage/target.message")
    assert object_path.current_name_text() == "target.message"

    object_path.push_value("/stage/missing/deep.value")
    assert object_path.current_name_text() == "deep.value"
