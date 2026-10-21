from nyx.api.v1 import NYX_REGISTRY, Node, NodeComponent, Stage, StageObject, commands
from nyx.core.models.registry_model import RegistryListModel


def test_description_is_empty_by_default():
    assert StageObject.get_description() == ""
    assert Node.get_description() == ""
    assert NodeComponent.get_description() == ""


# The registry is filled when the plugins are initialized, after the tests are
# collected, so the types are looked at while the tests run.


def test_every_registered_node_has_a_description():
    assert NYX_REGISTRY.nodes
    missing = [
        type_id
        for type_id, node_cls in NYX_REGISTRY.nodes.items()
        if not node_cls.get_description().strip()
    ]
    assert not missing


def test_every_registered_component_has_a_description():
    assert NYX_REGISTRY.node_components
    missing = [
        type_id
        for type_id, cpnt_cls in NYX_REGISTRY.node_components.items()
        if not cpnt_cls.get_description().strip()
    ]
    assert not missing


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
