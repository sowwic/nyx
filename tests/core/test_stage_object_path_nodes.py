import logging
import pathlib

import pytest
from PySide6 import QtCore

from nyx.api.v1 import (
    CoreNodeComponents,
    CoreNodes,
    NodeComponentFlag,
    Stage,
    commands,
    exceptions,
    static_vars,
)
from nyx.core.contexts.serialization import NodeDeserializationContext
from nyx.plugins.core.node_components.object_path import StageObjectPathComponent


def create(stage, type_id=CoreNodes.ACTION, name=None, parent=None):
    command = commands.CreateNodeCommand(
        stage=stage, type_id=type_id, name=name, parent_node=parent
    )
    stage.push_command(command)
    return command.result_node


def create_owner(stage, name="getter", parent=None):
    """Create a node holding a `StageObjectPathComponent` named "node_path"."""
    node = create(stage, CoreNodes.ACTION, name=name, parent=parent)
    command = commands.AddNodeComponentCommand(
        node=node, type_id=CoreNodeComponents.STAGE_OBJECT_PATH, name="node_path"
    )
    stage.push_command(command)
    command.result_component.writable = True
    return node


def paste(stage, nodes, parent=None):
    command = commands.PasteNodesCommand(
        stage=stage,
        serialize_nodes=[node.serialize() for node in nodes],
        position=QtCore.QPointF(0, 0),
        parent_node=parent,
    )
    stage.push_command(command)
    return command.pasted_nodes


@pytest.fixture
def getter_and_target():
    """Stage with a getter pointing at a log node, both at the stage root."""
    stage = Stage()
    target = create(stage, CoreNodes.LOG, name="target")
    getter = create_owner(stage, name="getter")
    getter["node_path"].push_value(target.path.as_posix())
    return stage, getter, target


# ======== Component ========= #


def test_object_path_has_its_own_type():
    component = StageObjectPathComponent()
    assert component.get_type_id() == CoreNodeComponents.STAGE_OBJECT_PATH
    assert component.is_editable
    assert NodeComponentFlag.STATIC in component.component_flags
    assert not component.is_valid  # nothing to point at while detached
    assert component.target_node is None


def test_absolute_path_resolves_to_node_and_uuid(getter_and_target):
    _stage, getter, target = getter_and_target
    object_path = getter["node_path"]
    assert object_path.target_node is target
    assert object_path.target_uuid == target.uuid
    assert object_path.resolve_node() is target
    assert object_path.pull_value() == target.path.as_posix()  # consumers get the path
    assert object_path.get_display_value() == str(target)  # views get the node
    assert object_path.get_display_value() == "LogNode (/stage/target)"
    assert object_path.is_valid


@pytest.mark.parametrize("text", ["target", "./target", "../stage/target"])
def test_relative_path_resolves_against_scope_of_owner(getter_and_target, text):
    _stage, getter, target = getter_and_target
    getter["node_path"].push_value(text)
    assert getter["node_path"].resolve_node() is target
    assert getter["node_path"].pull_value() == target.path.as_posix()


def test_relative_path_in_child_scope():
    stage = Stage()
    group = create(stage, CoreNodes.ACTION, name="group")
    target = create(stage, CoreNodes.LOG, name="target", parent=group)
    getter = create_owner(stage, name="getter", parent=group)
    outer = create(stage, CoreNodes.LOG, name="outer")

    getter["node_path"].push_value("./target")
    assert getter["node_path"].resolve_node() is target
    getter["node_path"].push_value("../outer")
    assert getter["node_path"].resolve_node() is outer


def test_object_path_follows_renamed_target(getter_and_target):
    _stage, getter, target = getter_and_target
    object_path = getter["node_path"]
    target.rename("renamed")

    assert object_path.resolve_node() is target
    assert object_path.pull_value() == target.path.as_posix()
    assert object_path.pull_value().endswith("/renamed")


def test_missing_target_is_unresolved(getter_and_target):
    _stage, getter, _target = getter_and_target
    object_path = getter["node_path"]
    object_path.push_value("/stage/does_not_exist")

    assert object_path.target_node is None
    assert not object_path.is_valid
    assert object_path.pull_value() == "/stage/does_not_exist"  # what was typed
    with pytest.raises(exceptions.StageObjectQueryError):
        object_path.resolve_node()


@pytest.mark.parametrize("text", [None, "", "   "])
def test_empty_object_path_is_unresolved(getter_and_target, text):
    _stage, getter, _target = getter_and_target
    getter["node_path"].push_value(text)
    assert not getter["node_path"].is_valid


def test_path_is_not_evaluated(getter_and_target, caplog):
    _stage, getter, target = getter_and_target
    with caplog.at_level(logging.WARNING):
        getter["node_path"].push_value(target.path.as_posix())
        getter["node_path"].push_value("target", evaluate=True)
    assert "Failed to eval" not in caplog.text


def test_linked_object_path_provides_the_path():
    stage = Stage()
    target = create(stage, CoreNodes.LOG, name="target")
    owner = create_owner(stage, name="owner")
    source_node = create_owner(stage, name="source")
    source = source_node["node_path"]
    source.readable = True
    source.push_value(target.path.as_posix())

    stage.push_command(
        commands.LinkNodeComponentsCommand(
            stage=stage, source=source, target=owner["node_path"]
        )
    )
    assert owner["node_path"].resolve_node() is target
    source.push_value("/stage/nowhere")
    assert not owner["node_path"].is_valid


def test_plain_value_can_be_linked_into_a_object_path():
    stage = Stage()
    owner = create_owner(stage, name="owner")
    source_node = create(stage, CoreNodes.ACTION, name="source")
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
            target=owner["node_path"],
        )
    )
    assert len(owner["node_path"].input_links) == 1


def test_set_value_command_undo_redo(getter_and_target):
    stage, getter, target = getter_and_target
    other = create(stage, CoreNodes.LOG, name="other")
    object_path = getter["node_path"]

    stage.push_command(
        commands.SetNodeComponentValueCommand(
            stage=stage,
            node_component=object_path,
            value=other.path.as_posix(),
            raw=True,
        )
    )
    assert object_path.resolve_node() is other
    stage.undo_stack.undo()
    assert object_path.resolve_node() is target
    stage.undo_stack.redo()
    assert object_path.resolve_node() is other


def test_object_path_survives_delete_and_undo_of_target(getter_and_target):
    stage, getter, target = getter_and_target
    object_path = getter["node_path"]

    stage.push_command(commands.DeleteNodeCommand(stage=stage, nodes=[target]))
    assert not object_path.is_valid
    stage.undo_stack.undo()
    assert object_path.is_valid
    assert object_path.resolve_node().name == "target"


# ======== Serialization ========= #


def test_serialized_value_has_uuid_and_scope_relative_path(getter_and_target):
    _stage, getter, target = getter_and_target
    value = getter["node_path"].serialize_value()
    assert value == {"target_uuid": str(target.uuid), "path": "target"}


def test_export_import_roundtrip(output_dir: pathlib.Path, getter_and_target):
    stage, getter, target = getter_and_target
    export_path = output_dir / f"roundtrip{Stage.FILE_EXTENSION}"
    stage.export_json(export_path)

    other_stage = Stage()
    other_stage.import_json(export_path)

    assert stage.root_node.serialize() == other_stage.root_node.serialize()
    new_getter = other_stage.get_object(getter.path)
    assert new_getter["node_path"].resolve_node().path == target.path


def test_plain_path_value_still_loads():
    stage = Stage()
    target = create(stage, CoreNodes.LOG, name="target")
    owner = create_owner(stage, name="owner")
    serialized = owner.serialize()
    for component in serialized["components"]:
        if component["name"] == "node_path":
            component["value"] = target.path.as_posix()  # a plain path, not a dict

    other_stage = Stage()
    create(other_stage, CoreNodes.LOG, name="target")
    (pasted,) = paste(other_stage, [_Serialized(serialized)])
    assert pasted["node_path"].get_type_id() == CoreNodeComponents.STAGE_OBJECT_PATH
    assert pasted["node_path"].resolve_node().path == target.path


class _Serialized:
    """Stands in for a node when only its serialized data is at hand."""

    def __init__(self, data):
        self._data = data

    def serialize(self):
        return self._data


# ======== Pasting and importing ========= #


@pytest.mark.parametrize("getter_first", [True, False])
def test_pasting_group_in_same_scope_points_copies_at_each_other(
    getter_and_target, getter_first
):
    stage, getter, target = getter_and_target
    nodes = [getter, target] if getter_first else [target, getter]

    pasted = paste(stage, nodes)
    new_getter = next(node for node in pasted if node.get_type_id() == CoreNodes.ACTION)
    new_target = next(node for node in pasted if node.get_type_id() == CoreNodes.LOG)

    assert new_target is not target
    assert new_getter["node_path"].resolve_node() is new_target
    assert getter["node_path"].resolve_node() is target  # the originals are untouched
    assert new_getter["node_path"].is_valid


def test_pasting_only_the_getter_keeps_pointing_at_the_original(getter_and_target):
    stage, getter, target = getter_and_target
    (new_getter,) = paste(stage, [getter])
    assert new_getter["node_path"].resolve_node() is target


def test_pasting_group_into_another_stage_points_at_the_copies(getter_and_target):
    _stage, getter, target = getter_and_target
    other_stage = Stage()

    pasted = paste(other_stage, [getter, target])
    new_getter = next(node for node in pasted if node.get_type_id() == CoreNodes.ACTION)
    new_target = next(node for node in pasted if node.get_type_id() == CoreNodes.LOG)

    assert new_getter["node_path"].resolve_node() is new_target
    assert new_getter.stage is other_stage


def test_pasting_group_into_a_child_scope_follows_the_group():
    stage = Stage()
    target = create(stage, CoreNodes.LOG, name="target")
    getter = create_owner(stage, name="getter")
    getter["node_path"].push_value("./target")
    destination = create(stage, CoreNodes.ACTION, name="destination")

    pasted = paste(stage, [getter, target], parent=destination)
    new_getter = next(node for node in pasted if node.get_type_id() == CoreNodes.ACTION)
    new_target = next(node for node in pasted if node.get_type_id() == CoreNodes.LOG)

    assert new_target.parent() is destination
    assert new_getter["node_path"].resolve_node() is new_target
    assert new_getter["node_path"].pull_value() == "/stage/destination/target"


def test_external_target_in_another_stage_falls_back_to_relative_path(
    getter_and_target,
):
    _stage, getter, _target = getter_and_target
    other_stage = Stage()
    local_target = create(other_stage, CoreNodes.LOG, name="target")

    (new_getter,) = paste(other_stage, [getter])
    assert new_getter["node_path"].resolve_node() is local_target


def test_external_target_missing_in_another_stage_is_unresolved(getter_and_target):
    _stage, getter, _target = getter_and_target
    other_stage = Stage()

    (new_getter,) = paste(other_stage, [getter])
    assert not new_getter["node_path"].is_valid
    # ...and found once something shows up where the object_path looks
    create(other_stage, CoreNodes.LOG, name="target")
    assert new_getter["node_path"].is_valid


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

    new_getter = next(
        node for node in command.pasted_nodes if node.get_type_id() == CoreNodes.ACTION
    )
    new_target = next(
        node for node in command.pasted_nodes if node.get_type_id() == CoreNodes.LOG
    )
    assert new_getter["node_path"].resolve_node() is new_target


# ======== Context ========= #


def test_deferred_callbacks_run_once_in_order():
    context = NodeDeserializationContext(stage=Stage())
    calls = []
    context.defer(lambda: calls.append(1))
    context.defer(lambda: calls.append(2))

    context.run_deferred()
    context.run_deferred()
    assert calls == [1, 2]


# ======== Notifying views ========= #


def _record_changes(component):
    """Record what the model reports on each change, and what it answers right then."""
    model = component.model()
    index = component.index()
    changes = []

    def on_changed(top_left, _bottom_right, roles):
        if top_left != index:
            return
        changes.append(
            {
                "roles": set(roles),
                "display": index.data(component.Roles.DISPLAY_VALUE),
                "valid": index.data(component.Roles.IS_VALID),
            }
        )

    model.dataChanged.connect(on_changed)
    return changes


def test_views_are_told_when_the_object_path_becomes_valid():
    stage = Stage()
    getter = create_owner(stage, name="getter")
    object_path = getter["node_path"]
    object_path.push_value("/stage/missing")
    assert not object_path.is_valid
    changes = _record_changes(object_path)

    object_path.push_value(static_vars.ROOT_NODE_PATH.as_posix())

    reported_valid = [c for c in changes if object_path.Roles.IS_VALID in c["roles"]]
    assert reported_valid, "nothing told the views that validity changed"
    assert reported_valid[-1]["valid"] is True


def test_views_never_end_up_with_the_previous_display_value():
    stage = Stage()
    create(stage, CoreNodes.LOG, name="node")
    getter = create_owner(stage, name="getter")
    object_path = getter["node_path"]
    object_path.push_value(static_vars.ROOT_NODE_PATH.as_posix())
    changes = _record_changes(object_path)

    object_path.push_value("/stage/node")
    new_target = stage.root_node.find_child_by_name("node")

    reported_display = [
        c for c in changes if object_path.Roles.DISPLAY_VALUE in c["roles"]
    ]
    assert reported_display, "nothing told the views that the display changed"
    assert reported_display[-1]["display"] == str(new_target)
    assert all(c["display"] != str(stage.root_node) for c in reported_display)
