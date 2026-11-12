import pytest

from nyx.api.v1 import CoreDatatypes, CoreNodeComponents, CoreNodes, Stage, commands
from nyx.core.node import Node
from nyx.static.enums import NodeComponentFlag
from stage_helpers import STAGES

"""Stages of the running test: a node doesn't keep its stage alive."""


def new_node(literal):
    stage = Stage()
    STAGES.append(stage)
    command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.EMPTY)
    stage.push_command(command)
    node = command.result_node
    component = node.components_model.create_component(CoreNodeComponents.VALUE)
    component.name = "text"
    component.set_datatype(CoreDatatypes.STRING)
    component.is_literal = literal
    node.components_model.add_component(component)
    return node, component


@pytest.mark.parametrize("text", ["1 + 1", "max", "None", "print('not run')"])
def test_a_literal_component_keeps_text_as_typed(text):
    _, component = new_node(literal=True)

    component.push_value(text)

    assert component.pull_value() == text
    assert component.raw_value == text


def test_without_the_flag_text_is_evaluated():
    _, component = new_node(literal=False)

    component.push_value("1 + 1")

    assert component.pull_value() == "2"


def test_a_literal_component_never_runs_what_is_typed(capsys):
    _, component = new_node(literal=True)

    component.push_value("print('ran')")

    assert "ran" not in capsys.readouterr().out


def test_setting_the_flag_on_a_component_with_a_value_evaluates_it_again():
    _, component = new_node(literal=False)
    component.push_value("1 + 1")
    assert component.pull_value() == "2"

    component.is_literal = True
    assert component.pull_value() == "1 + 1"

    component.is_literal = False
    assert component.pull_value() == "2"


def test_the_flag_is_part_of_the_component_flags():
    _, component = new_node(literal=True)

    assert component.is_literal
    assert NodeComponentFlag.LITERAL in component.component_flags
    component.is_literal = False
    assert not component.is_literal


def test_existing_flag_values_keep_their_meaning():
    # Saved files hold the integers: the new flag must come after the old ones.
    assert NodeComponentFlag.INSPECTOR_HIDDEN.value < NodeComponentFlag.LITERAL.value
    assert NodeComponentFlag(NodeComponentFlag.INSPECTOR_HIDDEN.value) == (
        NodeComponentFlag.INSPECTOR_HIDDEN
    )


def test_the_flag_survives_serialization():
    node, component = new_node(literal=True)
    component.push_value("1 + 1")
    data = node.serialize()
    restored_stage = Stage()
    STAGES.append(restored_stage)

    restored = Node.deserialize(
        serialized_node=data, parent_node=restored_stage.root_node
    )

    restored_component = restored["text"]
    assert restored_component.is_literal
    assert restored_component.pull_value() == "1 + 1"


def test_a_component_saved_without_the_flag_stays_not_literal():
    node, component = new_node(literal=False)
    component.push_value("1 + 1")
    data = node.serialize()
    restored_stage = Stage()
    STAGES.append(restored_stage)

    restored = Node.deserialize(
        serialized_node=data, parent_node=restored_stage.root_node
    )

    assert not restored["text"].is_literal
    assert restored["text"].pull_value() == "2"
