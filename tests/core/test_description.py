import pytest

from nyx.api.v1 import NYX_REGISTRY, Node, NodeComponent, Stage, StageObject, commands
from nyx.core.models.registry_model import RegistryListModel


def test_description_is_empty_by_default():
    assert StageObject.get_description() == ""
    assert Node.get_description() == ""
    assert NodeComponent.get_description() == ""


@pytest.mark.parametrize("type_id", sorted(NYX_REGISTRY.nodes))
def test_every_registered_node_has_a_description(type_id):
    assert NYX_REGISTRY.nodes[type_id].get_description().strip()


@pytest.mark.parametrize("type_id", sorted(NYX_REGISTRY.node_components))
def test_every_registered_component_has_a_description(type_id):
    assert NYX_REGISTRY.node_components[type_id].get_description().strip()


def test_node_and_component_expose_the_description_role():
    stage = Stage()
    command = commands.CreateNodeCommand(stage=stage, type_id="core:branch")
    stage.push_command(command)
    node = command.result_node

    assert node.data(Node.Roles.DESCRIPTION) == type(node).get_description()
    assert node["condition"].data(NodeComponent.Roles.DESCRIPTION) == (
        type(node["condition"]).get_description()
    )


def test_registry_model_provides_the_description():
    model = RegistryListModel(lambda: NYX_REGISTRY.nodes)
    names = model.roleNames()
    assert names[RegistryListModel.Roles.DESCRIPTION] == b"description"

    for row in range(model.rowCount()):
        index = model.index(row)
        cls = index.data(RegistryListModel.Roles.TYPE_CLASS)
        assert index.data(RegistryListModel.Roles.DESCRIPTION) == cls.get_description()
