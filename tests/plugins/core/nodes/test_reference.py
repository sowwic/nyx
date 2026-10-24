import json
import pathlib
import uuid
from collections import OrderedDict

import pytest
from PySide6 import QtCore

from nyx.plugins.core.nodes.reference import ReferenceNode
from nyx.api.v1 import (
    CoreDatatypes,
    CoreNodeComponents,
    CoreNodes,
    Node,
    NodeComponent,
    NodeFlag,
    Stage,
    commands,
    exceptions,
)


def add_component(stage, node, name, value, datatype=CoreDatatypes.INT):
    command = commands.AddNodeComponentCommand(
        node=node, type_id=CoreNodeComponents.VALUE, name=name
    )
    stage.push_command(command)
    component = command.result_component
    component.set_datatype(datatype)
    component.push_value(value)
    component.is_editable = True
    component.readable = True
    component.writable = True
    return component


def create(stage, type_id, name=None, parent=None):
    command = commands.CreateNodeCommand(
        stage=stage, type_id=type_id, name=name, parent_node=parent
    )
    stage.push_command(command)
    return command.result_node


def make_source(path: pathlib.Path) -> Stage:
    """Stage file with two top components and an inner node fed by one of them."""
    source = Stage()
    add_component(source, source.root_node, "amount", 5)
    add_component(source, source.root_node, "label", "hello", CoreDatatypes.STRING)
    inner = create(source, CoreNodes.VALUE, name="inner")
    inner["value"].set_datatype(CoreDatatypes.INT)
    inner["value"].writable = True
    source.push_command(
        commands.LinkNodeComponentsCommand(
            stage=source, source=source.root_node["amount"], target=inner["value"]
        )
    )
    source.export_json(path)
    return source


def reference(stage, source_path, name="ref") -> Node:
    node = create(stage, CoreNodes.REFERENCE, name=name)
    node["source"].push_value(str(source_path))
    return node


def at(stage: Stage, path: str):
    return stage.get_object(pathlib.PurePosixPath("/stage" + path))


def reopen(stage: Stage, path: pathlib.Path) -> Stage:
    stage.export_json(path)
    reopened = Stage()
    reopened.import_json(path)
    return reopened


@pytest.fixture
def source_path(tmp_path) -> pathlib.Path:
    path = tmp_path / f"source{Stage.FILE_EXTENSION}"
    make_source(path)
    return path


def test_reference_has_source_and_is_creatable():
    stage = Stage()
    node = create(stage, CoreNodes.REFERENCE)

    assert node.get_type_id() == CoreNodes.REFERENCE
    assert node["source"].get_type_id() == CoreNodeComponents.FILE
    assert node["source"].datatype_id == CoreDatatypes.STRING
    assert node.load_error == "No source set"


def test_node_flags():
    assert Node.get_type_flags() == NodeFlag.NONE
    flags = ReferenceNode.get_type_flags()
    assert NodeFlag.LOCKS_CHILDREN in flags
    assert NodeFlag.LOCKS_STRUCTURE in flags


def test_children_of_a_reference_have_a_locked_structure(source_path):
    stage = Stage()
    node = reference(stage, source_path)
    inner = node.find_child_by_name("inner")

    assert node.locks_children and node.locks_structure
    assert not inner.locks_structure
    assert inner.is_structure_locked
    assert not create(stage, CoreNodes.VALUE).is_structure_locked


def test_reference_takes_top_components_and_children(source_path):
    stage = Stage()
    node = reference(stage, source_path)

    assert node.load_error == ""
    assert node["amount"].raw_value == 5
    assert node["label"].raw_value == "hello"
    assert node["amount"].is_built_in
    inner = node.find_child_by_name("inner")
    assert inner is not None
    assert inner.is_locked
    assert not node.is_locked
    # The link inside the source works: the top component feeds the inner node.
    assert inner["value"].input_links[0].source_component is node["amount"]


def test_values_and_links_to_the_reference_survive_reopen(tmp_path, source_path):
    stage = Stage()
    node = reference(stage, source_path)
    node["amount"].push_value(42)
    sink = create(stage, CoreNodes.VALUE, name="sink")
    sink["value"].set_datatype(CoreDatatypes.INT)
    sink["value"].writable = True
    stage.push_command(
        commands.LinkNodeComponentsCommand(
            stage=stage, source=node["amount"], target=sink["value"]
        )
    )

    reopened = reopen(stage, tmp_path / f"second{Stage.FILE_EXTENSION}")

    new_node = at(reopened, "/ref")
    assert new_node["amount"].raw_value == 42
    assert new_node.find_child_by_name("inner") is not None
    assert new_node.find_child_by_name("inner")["value"].input_links
    sink_value = at(reopened, "/sink")["value"]
    assert sink_value.input_links[0].source_component is new_node["amount"]
    # Children aren't stored with the stage.
    saved = json.loads((tmp_path / f"second{Stage.FILE_EXTENSION}").read_text())
    ref_data = next(c for c in saved["children"] if c["name"] == "ref")
    assert "children" not in ref_data
    assert len(saved["links"]) == 1


def test_changes_to_the_source_are_pulled_in(tmp_path, source_path, caplog):
    stage = Stage()
    node = reference(stage, source_path)
    node["amount"].push_value(42)
    saved = tmp_path / f"second{Stage.FILE_EXTENSION}"
    stage.export_json(saved)

    source = Stage()
    source.import_json(source_path)
    source.root_node["label"].push_value("changed")
    add_component(source, source.root_node, "extra", 1)
    source.push_command(
        commands.DeleteNodeComponentCommand(
            node=source.root_node, component_names=["amount"]
        )
    )
    add_component(source, source.root_node, "amount", 7)
    source.export_json(source_path)

    reopened = Stage()
    with caplog.at_level("WARNING"):
        reopened.import_json(saved)
    new_node = at(reopened, "/ref")
    assert new_node["label"].raw_value == "changed"
    assert new_node["extra"].raw_value == 1
    # Set on this node, so the source can't take it back.
    assert new_node["amount"].raw_value == 42


def test_reload_removes_components_that_left_the_source(tmp_path, source_path):
    stage = Stage()
    node = reference(stage, source_path)

    source = Stage()
    source.import_json(source_path)
    source.push_command(
        commands.DeleteNodeComponentCommand(
            node=source.root_node, component_names=["label"]
        )
    )
    source.export_json(source_path)
    node.reload()

    with pytest.raises(ValueError):
        node["label"]
    assert node["amount"].raw_value == 5


def test_changing_the_source_loads_the_new_file(tmp_path, source_path):
    other = tmp_path / f"other{Stage.FILE_EXTENSION}"
    other_stage = Stage()
    add_component(other_stage, other_stage.root_node, "speed", 3)
    other_stage.export_json(other)

    stage = Stage()
    node = reference(stage, source_path)
    node["source"].push_value(str(other))

    assert node["speed"].raw_value == 3
    assert node.find_child_by_name("inner") is None
    with pytest.raises(ValueError):
        node["amount"]


def test_changing_the_source_to_a_missing_file_removes_the_components(
    tmp_path, source_path
):
    stage = Stage()
    node = reference(stage, source_path)
    link_to_reference(stage, node, "label")

    node["source"].push_value(str(tmp_path / f"missing{Stage.FILE_EXTENSION}"))
    QtCore.QCoreApplication.processEvents()

    assert "doesn't exist" in node.load_error
    assert node.find_child_by_name("inner") is None
    assert [c.name for c in node.components_model.list_components()] == ["source"]
    assert stage.undo_stack.count() == 0


def test_clearing_the_source_removes_the_components(source_path):
    stage = Stage()
    node = reference(stage, source_path)

    node["source"].push_value("")

    assert node.load_error == "No source set"
    assert [c.name for c in node.components_model.list_components()] == ["source"]


def test_relative_source_is_relative_to_the_stage_file(tmp_path, source_path):
    stage = Stage()
    node = create(stage, CoreNodes.REFERENCE, name="ref")
    node["source"].push_value(source_path.name)
    assert node.load_error != ""

    stage.export_json(tmp_path / f"stage{Stage.FILE_EXTENSION}")
    node.reload()

    assert node.load_error == ""
    assert node["amount"].raw_value == 5


# ======== History ========= #


def link_to_reference(stage, node, name):
    """Link a new string value node into a component of the reference."""
    feeder = create(stage, CoreNodes.VALUE, name="feeder")
    feeder["value"].set_datatype(CoreDatatypes.STRING)
    stage.push_command(
        commands.LinkNodeComponentsCommand(
            stage=stage, source=feeder["value"], target=node[name]
        )
    )


def remove_from_source(path, name):
    source = Stage()
    source.import_json(path)
    source.push_command(
        commands.DeleteNodeComponentCommand(
            node=source.root_node, component_names=[name]
        )
    )
    source.export_json(path)


def test_removing_a_component_from_the_source_clears_the_undo_history(
    tmp_path, source_path
):
    stage = Stage()
    node = reference(stage, source_path)
    node["label"].writable = True
    link_to_reference(stage, node, "label")
    assert stage.undo_stack.count() > 0

    remove_from_source(source_path, "label")
    node.reload()
    QtCore.QCoreApplication.processEvents()

    assert stage.undo_stack.count() == 0
    stage.undo_stack.undo()
    stage.undo_stack.redo()
    assert stage.is_modified()
    with pytest.raises(ValueError):
        node["label"]


def test_reload_that_removes_nothing_keeps_the_undo_history(tmp_path, source_path):
    stage = Stage()
    node = reference(stage, source_path)
    node["label"].writable = True
    link_to_reference(stage, node, "label")
    count = stage.undo_stack.count()

    node.reload()
    QtCore.QCoreApplication.processEvents()

    assert stage.undo_stack.count() == count
    assert node["label"].input_links


def test_changing_the_source_to_a_file_without_the_component_clears_the_history(
    tmp_path, source_path
):
    other = tmp_path / f"other{Stage.FILE_EXTENSION}"
    Stage().export_json(other)
    stage = Stage()
    node = reference(stage, source_path)
    node["label"].writable = True
    link_to_reference(stage, node, "label")

    stage.push_command(
        commands.SetNodeComponentValueCommand(
            stage=stage, node_component=node["source"], value=str(other)
        )
    )
    QtCore.QCoreApplication.processEvents()

    assert stage.undo_stack.count() == 0
    stage.undo_stack.undo()


# ======== Locking ========= #


def test_children_cant_be_changed(source_path):
    stage = Stage()
    node = reference(stage, source_path)
    inner = node.find_child_by_name("inner")

    with pytest.raises(exceptions.NyxCommandValidationError):
        stage.push_command(commands.DeleteNodeCommand(stage=stage, nodes=[inner]))
    with pytest.raises(exceptions.NyxCommandValidationError):
        stage.push_command(
            commands.RenameNodeCommand(stage=stage, node=inner, new_name="other")
        )
    with pytest.raises(exceptions.NyxCommandValidationError):
        stage.push_command(
            commands.SetNodeComponentValueCommand(
                stage=stage, node_component=inner["value"], value=3
            )
        )
    with pytest.raises(exceptions.NyxCommandValidationError):
        stage.push_command(
            commands.AddNodeComponentCommand(
                node=inner, type_id=CoreNodeComponents.VALUE, name="x"
            )
        )
    with pytest.raises(exceptions.NyxCommandValidationError):
        stage.push_command(
            commands.CreateNodeCommand(
                stage=stage, type_id=CoreNodes.VALUE, parent_node=inner
            )
        )


def test_views_cant_edit_the_values_of_the_children(source_path):
    stage = Stage()
    node = reference(stage, source_path)
    inner = node.find_child_by_name("inner")
    outside = create(stage, CoreNodes.VALUE, name="outside")

    def editable(component):
        model = component.model()
        return model.data(component.index(), NodeComponent.Roles.IS_EDITABLE)

    assert not editable(inner["value"])
    assert editable(node["amount"])
    assert editable(outside["value"])


def test_children_cant_be_linked(source_path):
    stage = Stage()
    node = reference(stage, source_path)
    inner = node.find_child_by_name("inner")
    outside = create(stage, CoreNodes.VALUE, name="outside")
    outside["value"].set_datatype(CoreDatatypes.INT)
    outside["value"].writable = True

    with pytest.raises(exceptions.NyxCommandValidationError):
        stage.push_command(
            commands.LinkNodeComponentsCommand(
                stage=stage, source=node["amount"], target=inner["value"]
            )
        )
    with pytest.raises(exceptions.NyxCommandValidationError):
        stage.push_command(
            commands.UnlinkNodeComponentsCommand(
                stage=stage, link_uuids=[inner["value"].input_links[0].uuid]
            )
        )


def test_reference_structure_is_locked_but_values_and_links_are_not(source_path):
    stage = Stage()
    node = reference(stage, source_path)

    for command in (
        commands.AddNodeComponentCommand(
            node=node, type_id=CoreNodeComponents.VALUE, name="x"
        ),
        commands.DeleteNodeComponentCommand(node=node, component_names=["amount"]),
        commands.SetNodeComponentDatatypeCommand(
            stage=stage, node_component=node["amount"], datatype_id=CoreDatatypes.FLOAT
        ),
        commands.RenameNodeComponentCommand(
            stage=stage, node_component=node["amount"], new_name="other"
        ),
    ):
        with pytest.raises(exceptions.NyxCommandValidationError):
            stage.push_command(command)

    stage.push_command(
        commands.SetNodeComponentValueCommand(
            stage=stage, node_component=node["amount"], value=9
        )
    )
    assert node["amount"].raw_value == 9
    # The node itself can be renamed and moved like any other.
    stage.push_command(
        commands.RenameNodeCommand(stage=stage, node=node, new_name="renamed")
    )
    assert node.name == "renamed"


def test_deleting_the_reference_removes_its_children_and_undo_restores_them(
    source_path,
):
    stage = Stage()
    node = reference(stage, source_path)
    stage.push_command(commands.DeleteNodeCommand(stage=stage, nodes=[node]))

    assert stage.node_from_path(pathlib.PurePosixPath("/stage/ref")) is None
    assert stage.node_from_path(pathlib.PurePosixPath("/stage/ref/inner")) is None

    stage.undo_stack.undo()
    restored = at(stage, "/ref")
    assert restored["amount"].raw_value == 5
    assert restored.find_child_by_name("inner") is not None


def test_datatype_of_reference_components_is_locked(source_path):
    stage = Stage()
    node = reference(stage, source_path)

    assert node["amount"].is_datatype_locked
    assert node.find_child_by_name("inner")["value"].is_datatype_locked


def test_pasted_reference_survives_undo_and_redo(source_path):
    stage = Stage()
    node = reference(stage, source_path)
    command = commands.PasteNodesCommand(
        stage=stage,
        serialize_nodes=[node.serialize()],
        position=QtCore.QPointF(0, 0),
        parent_node=None,
    )
    stage.push_command(command)

    stage.undo_stack.undo()
    assert not command.created_uuids
    stage.undo_stack.redo()

    pasted = command.pasted_nodes[0]
    assert pasted.get_type_id() == CoreNodes.REFERENCE
    assert pasted["amount"].raw_value == 5
    assert pasted.find_child_by_name("inner") is not None


def test_link_to_a_pasted_reference_survives_undo_and_redo(source_path):
    stage = Stage()
    pasted_data = OrderedDict(
        [
            ("uuid", str(uuid.uuid4())),
            ("name", "ref"),
            ("type_id", CoreNodes.REFERENCE),
            ("active", True),
            ("source", str(source_path)),
        ]
    )
    stage.push_command(
        commands.PasteNodesCommand(
            stage=stage,
            serialize_nodes=[pasted_data],
            position=QtCore.QPointF(0, 0),
            parent_node=None,
        )
    )
    node = at(stage, "/ref")
    feeder = create(stage, CoreNodes.VALUE, name="feeder")
    feeder["value"].set_datatype(CoreDatatypes.STRING)
    stage.push_command(
        commands.LinkNodeComponentsCommand(
            stage=stage, source=feeder["value"], target=node["label"]
        )
    )

    while stage.undo_stack.canUndo():
        stage.undo_stack.undo()
    assert stage.node_from_path(pathlib.PurePosixPath("/stage/ref")) is None
    while stage.undo_stack.canRedo():
        stage.undo_stack.redo()

    node = at(stage, "/ref")
    assert node["label"].input_links
    assert node["label"].input_links[0].source_component.node.name == "feeder"


# ======== Failures ========= #


def test_missing_source_keeps_components_and_links(tmp_path, source_path):
    stage = Stage()
    node = reference(stage, source_path)
    node["amount"].push_value(42)
    saved = tmp_path / f"second{Stage.FILE_EXTENSION}"
    stage.export_json(saved)
    source_path.unlink()

    reopened = Stage()
    reopened.import_json(saved)

    new_node = at(reopened, "/ref")
    assert "doesn't exist" in new_node.load_error
    assert new_node["amount"].raw_value == 42
    assert new_node.find_child_by_name("inner") is None


def test_reference_into_itself_is_an_error(tmp_path, source_path):
    stage = Stage()
    stage.export_json(source_path)
    node = reference(stage, source_path)

    assert node.load_error == "A stage can't reference itself"


def test_reference_cycle_is_an_error(tmp_path):
    first = tmp_path / f"first{Stage.FILE_EXTENSION}"
    second = tmp_path / f"second{Stage.FILE_EXTENSION}"
    stage_b = Stage()
    reference(stage_b, first, name="to_first")
    stage_b.export_json(second)
    stage_a = Stage()
    reference(stage_a, second, name="to_second")
    stage_a.export_json(first)

    reopened = Stage()
    reopened.import_json(first)

    inner = at(reopened, "/to_second/to_first")
    assert inner.load_error == "A stage can't reference itself"


def test_same_file_twice_has_independent_values(source_path):
    stage = Stage()
    first = reference(stage, source_path, name="first")
    second = reference(stage, source_path, name="second")
    first["amount"].push_value(1)
    second["amount"].push_value(2)

    assert first["amount"].raw_value == 1
    assert second["amount"].raw_value == 2
    assert first["amount"].uuid != second["amount"].uuid
    first_inner = first.find_child_by_name("inner")
    second_inner = second.find_child_by_name("inner")
    assert first_inner.uuid != second_inner.uuid
