from nyx.api.v1 import NYX_REGISTRY, NyxPluginManager


def test_include_enables_the_listed_plugins_even_if_they_were_disabled():
    manager = NyxPluginManager()
    function_plugin = "NyxMathFunctions"
    try:
        manager.initialize_plugins(include=["NyxCore"])
        assert NYX_REGISTRY.plugins[function_plugin].enabled is False
        assert NYX_REGISTRY.get_node_cls("function:math.add") is None

        manager.initialize_plugins(include=["NyxCore", function_plugin])

        assert NYX_REGISTRY.plugins[function_plugin].enabled is True
        assert NYX_REGISTRY.get_node_cls("function:math.add") is not None
        assert NYX_REGISTRY.plugins["NyxListFunctions"].enabled is False
    finally:
        # Leave every plugin on, as the rest of the tests expect
        for entry in NYX_REGISTRY.plugins.values():
            entry.enabled = True
        manager.initialize_plugins()
