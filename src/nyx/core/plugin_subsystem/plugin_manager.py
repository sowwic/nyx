import logging
import typing

from .plugin_loader import NyxPluginLoader
from .plugin_interface import NyxPluginInterface
from .registry import NYX_REGISTRY, NyxPluginRegistryEntry


LOGGER = logging.getLogger("NyxPluginManager")


class NyxPluginManager:
    """Central class for handling plugin registration, loading and initialization."""

    def __init__(self):
        """Initialize manager instance"""
        self._loader = NyxPluginLoader()

    @property
    def loader(self) -> NyxPluginLoader:
        return self._loader

    @loader.setter
    def loader(self, loader: NyxPluginLoader):
        if not isinstance(loader, NyxPluginLoader):
            raise TypeError(f"Loader must be of type: {NyxPluginLoader}")
        self._loader = loader

    @staticmethod
    def register_plugin() -> typing.Callable[[NyxPluginInterface], NyxPluginInterface]:
        """Decorator for plugin registration

        Returns:
            Decorator function


        Example:
            ```python
            from nyx.api.v1 import NyxPluginManager

            @NyxPluginManager.register_plugin()
            class MyPlugin(NyxPluginInterface):
                NAME = "my_plugin"
            ```
        """

        def _register_plugin_inner(plugin_cls: NyxPluginInterface) -> NyxPluginInterface:
            """Create new `NyxPluginRegistryEntry` for given plugin class.

            Args:
                plugin_cls: plugin class to register

            Returns:
                Same plugin class
            """
            try:
                NyxPluginManager.validate_plugin_class(plugin_cls)
            except Exception:
                LOGGER.exception("Failed to register %s", plugin_cls.__name__)
                return plugin_cls

            NYX_REGISTRY.add_plugin(plugin_cls)
            return plugin_cls

        return _register_plugin_inner

    @staticmethod
    def validate_plugin_class(plugin_cls: NyxPluginInterface) -> None:
        """Validate plugin class.

        Args:
            plugin_cls: plugin class to validate

        Raises:
            ValueError: Plugin NAME is not defined.
        """
        if not plugin_cls.NAME:
            raise ValueError("Plugin has no NAME defined")

        if plugin_cls.NAME in NYX_REGISTRY.plugins:
            raise ValueError(
                f"Plugin with name {plugin_cls.NAME} already exists:"
                f"{NYX_REGISTRY.plugins[plugin_cls.NAME]}"
            )

    def get_plugin(self, name: str) -> NyxPluginRegistryEntry | None:
        """Get plugin registry entry by name.

        Args:
            name: plugin name

        Returns:
            Plugin registry entry
        """
        return NYX_REGISTRY.plugins.get(name)

    def initialize_plugins(self, include: list[str] | None = None):
        """Iterate over registry and initialize each plugin."""
        NYX_REGISTRY.clear()
        self.loader.load_plugins_from_paths()

        for plugin_entry in NYX_REGISTRY.iter_plugin_entries():
            if include and plugin_entry.plugin_cls.NAME not in include:
                plugin_entry.enabled = False

            if not plugin_entry.enabled:
                continue

            plugin_entry.initialize()
            LOGGER.info(f"Initialized plugin: {plugin_entry.plugin_cls.NAME}")
        NYX_REGISTRY.register_plugin_content()
