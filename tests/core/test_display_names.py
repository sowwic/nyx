import pytest

from nyx.api.v1 import CoreNodeComponents, CoreNodes, Stage, commands
from nyx.core.exceptions import NyxCommandValidationError
from nyx.core.name_validator import NameValidator
from nyx.core.node import Node
from nyx.core.node_component import NodeComponent
from stage_helpers import STAGES

"""Stages of the running test: a node doesn't keep its stage alive."""


def new_stage():
    stage = Stage()
    STAGES.append(stage)
    return stage


def create(stage, type_id=CoreNodes.LOG, parent=None, name=None):
    command = commands.CreateNodeCommand(
        stage=stage, type_id=type_id, parent_node=parent, name=name
    )
    stage.push_command(command)
    return command.result_node


@pytest.mark.parametrize(
    ("display", "address"),
    [
        ("My cool node", "my_cool_node"),
        ("  Log  ", "log"),
        ("Hello, World!", "hello_world"),
        ("a--b__c", "a_b_c"),
        ("Step 2", "step_2"),
        ("???", ""),
        ("", ""),
    ],
)
def test_address_name_is_made_from_the_display_name(display, address):
    assert NameValidator.to_address_name(display) == address


@pytest.mark.parametrize(
    ("address", "display"),
    [("client_name", "Client Name"), ("log", "Log"), ("log1", "Log1"), ("", "")],
)
def test_display_name_can_be_made_from_an_address_name(address, display):
    assert NameValidator.humanize(address) == display


def test_new_nodes_get_the_type_display_name_and_unique_addresses():
    stage = new_stage()

    first, second, third = (create(stage) for _ in range(3))

    assert [n.display_name for n in (first, second, third)] == ["Log"] * 3
    assert [n.name for n in (first, second, third)] == ["log", "log1", "log2"]
    assert [n.text() for n in (first, second, third)] == ["Log"] * 3
    assert second.path.as_posix() == "/stage/log1"


def test_renaming_sets_the_display_name_and_the_address_follows():
    stage = new_stage()
    node = create(stage)

    stage.push_command(commands.RenameNodeCommand(stage, node, "My cool node"))

    assert node.display_name == "My cool node"
    assert node.name == "my_cool_node"
    assert node.path.as_posix() == "/stage/my_cool_node"
    assert node.text() == "My cool node"
    assert stage.get_object("/stage/my_cool_node") is node


def test_renamed_address_is_made_unique_among_the_siblings():
    stage = new_stage()
    first, second = create(stage), create(stage)

    stage.push_command(commands.RenameNodeCommand(stage, second, "Log"))

    assert (first.name, second.name) == ("log", "log1")
    assert second.display_name == "Log"


def test_renaming_to_what_the_address_already_is_keeps_it():
    stage = new_stage()
    node = create(stage)

    stage.push_command(commands.RenameNodeCommand(stage, node, "LOG"))

    assert (node.name, node.display_name) == ("log", "LOG")


def test_rename_can_be_undone_and_redone():
    stage = new_stage()
    node = create(stage)
    stage.push_command(commands.RenameNodeCommand(stage, node, "My cool node"))

    stage.undo_stack.undo()
    assert (node.name, node.display_name, node.text()) == ("log", "Log", "Log")

    stage.undo_stack.redo()
    assert (node.name, node.display_name) == ("my_cool_node", "My cool node")


def test_rename_to_a_name_without_letters_or_digits_is_refused():
    stage = new_stage()
    node = create(stage)

    with pytest.raises(NyxCommandValidationError):
        stage.push_command(commands.RenameNodeCommand(stage, node, "???"))

    assert node.display_name == "Log"


def test_views_show_address_names_when_the_stage_is_set_to():
    stage = new_stage()
    node = create(stage)
    stage.push_command(commands.RenameNodeCommand(stage, node, "My cool node"))
    changes = []
    stage.labels_changed.connect(lambda: changes.append(True))

    stage.show_address_names = True

    assert (node.label, node.text()) == ("my_cool_node", "my_cool_node")
    assert changes == [True]
    stage.push_command(commands.RenameNodeCommand(stage, node, "Other name"))
    assert node.text() == "other_name"

    stage.show_address_names = False
    assert node.text() == "Other name"


def test_nodes_created_while_addresses_are_shown_use_them():
    stage = new_stage()
    stage.show_address_names = True

    node = create(stage)

    assert node.text() == "log"


def test_names_survive_serialization():
    stage = new_stage()
    node = create(stage)
    stage.push_command(commands.RenameNodeCommand(stage, node, "My cool node"))
    data = node.serialize()

    other = new_stage()
    restored = Node.deserialize(serialized_node=data, parent_node=other.root_node)

    assert data["name"] == "my_cool_node"
    assert data["display_name"] == "My cool node"
    assert (restored.name, restored.display_name) == ("my_cool_node", "My cool node")


def test_data_without_a_display_name_gets_one_made_from_the_name():
    stage = new_stage()
    data = create(stage).serialize()
    del data["display_name"]
    data["name"] = "load_mesh"

    restored = Node.deserialize(serialized_node=data, parent_node=new_stage().root_node)

    assert (restored.name, restored.display_name) == ("load_mesh", "Load Mesh")


def test_deserializing_into_an_existing_node_sets_both_names():
    stage = new_stage()
    data = create(stage).serialize()
    data["name"], data["display_name"] = "other", "The Other"
    target = create(new_stage())

    Node.deserialize(serialized_node=data, node=target)

    assert (target.name, target.display_name) == ("other", "The Other")


# Components


def component_of(node, name):
    return node.components_model.get_component(name)


def test_component_display_names_are_made_from_their_names():
    node = create(new_stage(), CoreNodes.REMOTE_CLIENT)

    component = component_of(node, "client_name")

    assert component.display_name == "Client Name"
    assert component.label == "Client Name"


def test_renaming_a_component_sets_its_display_name_and_address():
    stage = new_stage()
    node = create(stage, CoreNodes.REMOTE_CLIENT)
    component = component_of(node, "client_name")

    stage.push_command(
        commands.RenameNodeComponentCommand(stage, component, "Who to wait for")
    )

    assert component.name == "who_to_wait_for"
    assert component.display_name == "Who to wait for"
    assert component.path.as_posix() == "/stage/remote_client.who_to_wait_for"
    assert component_of(node, "who_to_wait_for") is component


def test_component_rename_keeps_addresses_unique_and_can_be_undone():
    stage = new_stage()
    node = create(stage, CoreNodes.REMOTE_CLIENT)
    kind = component_of(node, "client_kind")

    stage.push_command(commands.RenameNodeComponentCommand(stage, kind, "Client Name"))
    assert kind.name == "client_name1"
    assert kind.display_name == "Client Name"

    stage.undo_stack.undo()
    assert (kind.name, kind.display_name) == ("client_kind", "Client Kind")


def test_component_rename_to_a_name_without_letters_or_digits_is_refused():
    stage = new_stage()
    node = create(stage, CoreNodes.REMOTE_CLIENT)

    with pytest.raises(NyxCommandValidationError):
        stage.push_command(
            commands.RenameNodeComponentCommand(
                stage, component_of(node, "client_name"), "!!"
            )
        )


def test_component_label_role_follows_the_stage_setting():
    stage = new_stage()
    node = create(stage, CoreNodes.REMOTE_CLIENT)
    component = component_of(node, "client_name")
    model = node.components_model
    role = NodeComponent.Roles.LABEL
    changed_roles = []
    model.dataChanged.connect(lambda *args: changed_roles.append(args[2]))

    assert model.data(component.index(), role) == "Client Name"
    stage.show_address_names = True

    assert model.data(component.index(), role) == "client_name"
    assert [role] in changed_roles


def test_component_names_survive_serialization():
    stage = new_stage()
    node = create(stage, CoreNodes.REMOTE_CLIENT)
    component = component_of(node, "client_name")
    stage.push_command(commands.RenameNodeComponentCommand(stage, component, "Who"))
    data = node.serialize()

    restored = Node.deserialize(serialized_node=data, parent_node=new_stage().root_node)

    assert component_of(restored, "who").display_name == "Who"


def test_component_without_a_display_name_in_the_data_gets_one_from_its_name():
    stage = new_stage()
    node = create(stage, CoreNodes.REMOTE_CLIENT)
    data = node.serialize()
    for component_data in data["components"]:
        component_data.pop("display_name")

    restored = Node.deserialize(serialized_node=data, parent_node=new_stage().root_node)

    assert component_of(restored, "client_kind").display_name == "Client Kind"


def test_plain_components_have_the_type_default_names():
    node = create(new_stage(), CoreNodes.EMPTY)
    component = node.components_model.create_component(CoreNodeComponents.VALUE)

    assert component.display_name == NameValidator.humanize(component.name)


def test_the_stage_root_is_displayed_as_stage():
    stage = new_stage()

    assert (stage.root_node.name, stage.root_node.display_name) == ("stage", "stage")
    assert stage.root_node.text() == "stage"


def test_loading_a_stage_keeps_the_root_display_name(tmp_path):
    stage = new_stage()
    data = stage.root_node.serialize()
    data["display_name"] = "Node"  # as saved by an earlier version
    other = new_stage()

    Node.deserialize(serialized_node=data, node=other.root_node)

    assert other.root_node.display_name == "stage"


def test_display_name_role_is_never_empty_for_views():
    stage = new_stage()
    node = create(stage, CoreNodes.REMOTE_CLIENT)
    component = component_of(node, "client_name")
    model = node.components_model
    role = NodeComponent.Roles.DISPLAY_NAME

    assert model.data(component.index(), role) == "Client Name"

    stage.push_command(commands.RenameNodeComponentCommand(stage, component, "Who"))
    assert model.data(component.index(), role) == "Who"
