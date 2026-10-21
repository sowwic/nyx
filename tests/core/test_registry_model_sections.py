from nyx.api.v1 import NYX_REGISTRY, StageObject
from nyx.core.models.registry_model import RegistryListModel


def test_type_without_source_plugin_has_no_plugin_name(monkeypatch):
    class Loose(StageObject):
        pass

    assert Loose.get_source_plugin_name() == ""


def test_registered_types_know_their_plugin():
    core_node = NYX_REGISTRY.nodes["core:branch"]
    core_component = NYX_REGISTRY.node_components["core:value"]

    assert core_node.get_source_plugin_name() == "NyxCore"
    assert core_component.get_source_plugin_name() == "NyxCore"


def test_registry_model_exposes_the_source_plugin_role():
    model = RegistryListModel(lambda: NYX_REGISTRY.nodes)

    assert model.roleNames()[RegistryListModel.Roles.SOURCE_PLUGIN] == b"sourcePlugin"
    for row in range(model.rowCount()):
        index = model.index(row)
        cls = index.data(RegistryListModel.Roles.TYPE_CLASS)
        assert index.data(RegistryListModel.Roles.SOURCE_PLUGIN) == (
            cls.get_source_plugin_name()
        )


def test_registry_model_keeps_the_types_of_a_plugin_together():
    model = RegistryListModel(lambda: NYX_REGISTRY.nodes)

    plugins = [
        model.index(row).data(RegistryListModel.Roles.SOURCE_PLUGIN)
        for row in range(model.rowCount())
    ]
    # No plugin shows up again after another one: one section per plugin
    seen = []
    for plugin in plugins:
        if not seen or seen[-1] != plugin:
            assert plugin not in seen
            seen.append(plugin)
    assert "NyxCore" in seen


def test_registry_model_provides_tags_as_a_sorted_list():
    model = RegistryListModel(lambda: NYX_REGISTRY.nodes)

    assert model.roleNames()[RegistryListModel.Roles.TYPE_TAGS] == b"typeTags"
    for row in range(model.rowCount()):
        index = model.index(row)
        cls = index.data(RegistryListModel.Roles.TYPE_CLASS)
        tags = index.data(RegistryListModel.Roles.TYPE_TAGS)
        assert isinstance(tags, list)
        assert tags == sorted(cls.get_tags())
