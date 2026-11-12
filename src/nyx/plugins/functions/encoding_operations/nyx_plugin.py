import typing

from nyx.api.v1 import NyxPluginManager, NyxPlugin

from . import operations


@NyxPluginManager.register_plugin()
class NyxEncodingFunctions(NyxPlugin):
    """Built-in plugin providing nodes for hashing and text encoding functions."""

    @classmethod
    def get_type_id(cls) -> str:
        """str: plugin id."""
        return "NyxEncodingFunctions"

    @classmethod
    def get_palette_name(cls) -> str:
        """str: name of the palette section."""
        return "Encoding Operations"

    @classmethod
    def initialize(cls) -> typing.Self:
        """Create the plugin and register a function node for every operation.

        Returns:
            typing.Self: initialized plugin.
        """
        plugin = cls()
        plugin.contents.register_function_module(operations, namespace="encoding")
        return plugin
