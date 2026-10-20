import pytest

from nyx.api.v1 import Stage, CoreNodes, CoreNodeComponents, CoreDatatypes, commands
from nyx.core.exceptions import NyxCommandValidationError


def make_condition(stage: Stage):
    command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.BRANCH)
    stage.push_command(command)
    return command.result_node["condition"]


def make_user_value(stage: Stage):
    node_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.EMPTY)
    stage.push_command(node_command)
    add = commands.AddNodeComponentCommand(
        node=node_command.result_node, type_id=CoreNodeComponents.VALUE
    )
    stage.push_command(add)
    return add.result_component


def test_set_datatype_is_undoable():
    stage = Stage()
    value = make_user_value(stage)
    value.push_value("5")

    stage.push_command(
        commands.SetNodeComponentDatatypeCommand(
            stage=stage, node_component=value, datatype_id=CoreDatatypes.STRING
        )
    )
    assert value.datatype_id == CoreDatatypes.STRING
    assert value.cached_value == "5"

    stage.undo_stack.undo()
    assert value.datatype_id == CoreDatatypes.OBJECT
    assert value.cached_value == 5

    stage.undo_stack.redo()
    assert value.datatype_id == CoreDatatypes.STRING


def test_built_in_component_datatype_is_locked():
    stage = Stage()
    condition = make_condition(stage)
    assert condition.is_built_in
    assert condition.is_datatype_locked

    with pytest.raises(NyxCommandValidationError, match="locked"):
        stage.push_command(
            commands.SetNodeComponentDatatypeCommand(
                stage=stage, node_component=condition, datatype_id=CoreDatatypes.INT
            )
        )
    assert condition.datatype_id == CoreDatatypes.BOOL


def make_linked_values(stage: Stage, datatype=CoreDatatypes.BOOL):
    source = make_user_value(stage)
    target = make_user_value(stage)
    source.readable = True
    target.writable = True
    source.set_datatype(datatype)
    target.set_datatype(datatype)
    link_command = commands.LinkNodeComponentsCommand(
        stage=stage, source=source, target=target
    )
    stage.push_command(link_command)
    return source, target, link_command


def change_datatype(stage, component, datatype_id):
    command = commands.SetNodeComponentDatatypeCommand(
        stage=stage, node_component=component, datatype_id=datatype_id
    )
    stage.push_command(command)
    return command


def test_incompatible_source_datatype_unlinks_components():
    stage = Stage()
    source, target, link_command = make_linked_values(stage)

    command = change_datatype(stage, source, CoreDatatypes.STRING)

    assert not source.links
    assert not target.links
    assert command.removed_link_uuids == [link_command.result_link_uuid]


def test_incompatible_target_datatype_unlinks_components():
    stage = Stage()
    source, target, _ = make_linked_values(stage)

    change_datatype(stage, target, CoreDatatypes.STRING)

    assert not source.links
    assert not target.links


def test_compatible_datatype_change_keeps_the_link():
    stage = Stage()
    source, target, _ = make_linked_values(stage)

    command = change_datatype(stage, source, CoreDatatypes.OBJECT)

    assert len(source.links) == 1
    assert command.removed_link_uuids == []


def test_undo_restores_datatype_and_link_with_the_same_uuid():
    stage = Stage()
    source, target, link_command = make_linked_values(stage)
    link_uuid = link_command.result_link_uuid

    change_datatype(stage, source, CoreDatatypes.STRING)
    stage.undo_stack.undo()

    assert source.datatype_id == CoreDatatypes.BOOL
    assert [link.uuid for link in source.links] == [link_uuid]

    stage.undo_stack.redo()
    assert source.datatype_id == CoreDatatypes.STRING
    assert not source.links


def test_links_of_components_inheriting_the_datatype_are_checked_too():
    stage = Stage()
    source = make_user_value(stage)
    source.readable = True
    source.set_datatype(CoreDatatypes.BOOL)
    setter_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.SET)
    stage.push_command(setter_command)
    middle = setter_command.result_node["value"]
    middle.readable = True
    end = make_user_value(stage)
    end.writable = True
    end.set_datatype(CoreDatatypes.BOOL)
    stage.push_command(
        commands.LinkNodeComponentsCommand(stage=stage, source=source, target=middle)
    )
    stage.push_command(
        commands.LinkNodeComponentsCommand(stage=stage, source=middle, target=end)
    )

    change_datatype(stage, source, CoreDatatypes.STRING)

    assert middle.datatype.type_id == CoreDatatypes.STRING
    assert len(source.links) == 1  # still compatible with the setter value
    assert not end.links  # the setter value is now a string, the end is a bool

    stage.undo_stack.undo()
    assert len(end.links) == 1


def test_value_invalid_for_the_new_datatype_is_replaced_by_its_default():
    stage = Stage()
    value = make_user_value(stage)
    value.push_value("abc")

    change_datatype(stage, value, CoreDatatypes.INT)

    assert value.raw_value == 0
    assert value.cached_value == 0
    assert value.is_valid


def test_valid_value_is_kept_when_the_datatype_changes():
    stage = Stage()
    value = make_user_value(stage)
    value.push_value("5")

    change_datatype(stage, value, CoreDatatypes.INT)

    assert value.raw_value == "5"
    assert value.cached_value == 5


def test_undo_restores_the_replaced_value():
    stage = Stage()
    value = make_user_value(stage)
    value.push_value("abc")

    change_datatype(stage, value, CoreDatatypes.INT)
    stage.undo_stack.undo()

    assert value.datatype_id == CoreDatatypes.OBJECT
    assert value.raw_value == "abc"
    assert value.cached_value == "abc"

    stage.undo_stack.redo()
    assert value.raw_value == 0


def test_links_of_a_getter_pointing_at_the_changed_component_are_checked_too():
    stage = Stage()
    target = make_user_value(stage)
    target.set_datatype(CoreDatatypes.BOOL)
    getter_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.GET)
    stage.push_command(getter_command)
    getter = getter_command.result_node
    getter["component"].push_value(target.path.as_posix())
    branch_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.BRANCH)
    stage.push_command(branch_command)
    condition = branch_command.result_node["condition"]
    link_command = commands.LinkNodeComponentsCommand(
        stage=stage, source=getter["value"], target=condition
    )
    stage.push_command(link_command)
    assert getter["value"].datatype.type_id == CoreDatatypes.BOOL
    assert len(condition.links) == 1

    command = change_datatype(stage, target, CoreDatatypes.FLOW)

    assert getter["value"].datatype.type_id == CoreDatatypes.FLOW
    assert not condition.links
    assert command.removed_link_uuids == [link_command.result_link_uuid]

    stage.undo_stack.undo()
    assert getter["value"].datatype.type_id == CoreDatatypes.BOOL
    assert len(condition.links) == 1
