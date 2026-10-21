import logging
import typing

from .plugin import NyxPlugin
from .plugin_loader import NyxPluginLoader
from .registry import NYX_REGISTRY, NyxPluginRegistryEntry
from ...utils.profiling import profile
from ..protocols.registry_entry import IRegistryEntry

LOGGER = logging.getLogger("NyxPluginManager")


class NyxPluginManager:
    """Central class for handling plugin registration, loading and initialization."""

    def __init__(self):
        """Initialize manager instance"""
        self._loader = NyxPluginLoader()

    @property
    def loader(self) -> NyxPluginLoader:
        """NyxPluginLoader: loader used to discover and import plugins."""
        return self._loader

    @loader.setter
    def loader(self, loader: NyxPluginLoader):
        if not isinstance(loader, NyxPluginLoader):
            raise TypeError(f"Loader must be of type: {NyxPluginLoader}")
        self._loader = loader

    @staticmethod
    def register_plugin() -> typing.Callable[[NyxPlugin], NyxPlugin]:
        """Decorator for plugin registration

        Returns:
            Decorator function


        Example:
            ```python
            from nyx.api.v1 import NyxPlugin, NyxPluginManager

            @NyxPluginManager.register_plugin()
            class MyPlugin(NyxPlugin):

            @classmethod
            def get_type_id(cls) -> str:
                return "MyPlugin"
            ```
        """

        def _register_plugin_inner(plugin_cls: NyxPlugin) -> NyxPlugin:
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
    def validate_plugin_class(plugin_cls: NyxPlugin) -> None:
        """Validate plugin class.

        Args:
            plugin_cls: plugin class to validate

        Raises:
            ValueError: Plugin NAME is not defined.
        """
        if not issubclass(plugin_cls, IRegistryEntry):
            raise TypeError(f"Not implemented {IRegistryEntry.__name__}: {plugin_cls}")

        if not plugin_cls.get_type_id():
            raise ValueError("Plugin has no type_id defined")

        type_id = plugin_cls.get_type_id()
        if type_id in NYX_REGISTRY.plugins:
            raise ValueError(
                f"Plugin with name {type_id} already exists:"
                f"{NYX_REGISTRY.plugins[type_id]}"
            )

    def get_plugin(self, name: str) -> NyxPluginRegistryEntry | None:
        """Get plugin registry entry by name.

        Args:
            name: plugin name

        Returns:
            Plugin registry entry
        """
        return NYX_REGISTRY.plugins.get(name)

    @profile(text="Plugins initialized in {seconds:.4f}s")
    def initialize_plugins(self, include: list[str] | None = None):
        """Iterate over registry and initialize each plugin.

        Args:
            include (list[str] | None): type ids of the plugins to use. Only these are
                enabled, whatever state an earlier call left them in. All enabled
                plugins are initialized if omitted.
        """
        self.loader.load_plugins_from_paths()

        initialization_counter = 0
        for plugin_entry in NYX_REGISTRY.iter_plugin_entries():
            type_id = plugin_entry.plugin_cls.get_type_id()
            if include:
                # Exactly these plugins, also the ones that an earlier call left disabled
                plugin_entry.enabled = type_id in include

            if not plugin_entry.enabled:
                continue

            if plugin_entry.plugin_instance is not None:
                continue

            plugin_entry.initialize()
            initialization_counter += 1
            LOGGER.info(f"Initialized plugin: {type_id}")

        LOGGER.info(
            f"Initialized {initialization_counter}/{len(NYX_REGISTRY.plugins)} plugins"
        )
        NYX_REGISTRY.register_plugin_content()
