import typing

from nyx.api.v1 import NyxPluginManager, NyxPlugin
from nyx.core.function_node import find_public_functions

from . import logic_operations, math_operations


@NyxPluginManager.register_plugin()
class NyxFunctions(NyxPlugin):
    """Built-in plugin providing nodes generated from plain functions."""

    @classmethod
    def get_type_id(cls) -> str:
        """str: plugin id."""
        return "NyxFunctions"

    @classmethod
    def initialize(cls) -> typing.Self:
        """Create the plugin and register a function node for every operation.

        Returns:
            typing.Self: initialized plugin.
        """
        plugin = cls()
        for module in (math_operations, logic_operations):
            group = module.__name__.rsplit(".", 1)[-1].removesuffix("_operations")
            for function in find_public_functions(module):
                plugin.contents.register_function_node(
                    function, type_id=f"function:{group}.{function.__name__}"
                )
        return plugin
