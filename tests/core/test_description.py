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
    # The condition describes itself, a component without a description of its own
    # has the one of its type
    assert node["condition"].description.startswith("Value that chooses the output")
    assert node["condition"].data(NodeComponent.Roles.DESCRIPTION) == (
        node["condition"].description
    )


def test_registry_model_provides_the_description():
    model = RegistryListModel(lambda: NYX_REGISTRY.nodes)
    names = model.roleNames()
    assert names[RegistryListModel.Roles.DESCRIPTION] == b"description"

    for row in range(model.rowCount()):
        index = model.index(row)
        cls = index.data(RegistryListModel.Roles.TYPE_CLASS)
        assert index.data(RegistryListModel.Roles.DESCRIPTION) == cls.get_description()


def make_node(stage, type_id):
    command = commands.CreateNodeCommand(stage=stage, type_id=type_id)
    stage.push_command(command)
    return command.result_node


def test_component_description_defaults_to_the_type_description():
    stage = Stage()
    node = make_node(stage, "core:node")
    command = commands.AddNodeComponentCommand(node=node, type_id="core:flow")
    stage.push_command(command)

    component = command.result_component
    assert component.description == type(component).get_description()


def test_component_description_can_be_changed():
    stage = Stage()
    node = make_node(stage, "core:branch")
    node["condition"].description = "Something else."

    assert node["condition"].description == "Something else."
    assert node.components_model.data(
        node["condition"].index(), NodeComponent.Roles.DESCRIPTION
    ) == ("Something else.")


def test_every_component_of_a_predefined_node_describes_itself():
    stage = Stage()
    for type_id, node_cls in NYX_REGISTRY.nodes.items():
        if type_id.startswith("function:"):
            continue
        node = make_node(stage, type_id)
        for component in node.components_model.list_components():
            assert component.description.strip(), f"{type_id}.{component.name}"
            # More than the name of the component type
            assert component.description != type(component).get_type_display_name(), (
                f"{type_id}.{component.name}"
            )
