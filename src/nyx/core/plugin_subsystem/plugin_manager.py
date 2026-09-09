import logging
import dataclasses
from collections import OrderedDict
from collections.abc import Callable, Iterator

from .plugin_loader import NyxPluginLoader
from .plugin_interface import NyxPluginInterface


LOGGER = logging.getLogger("NyxPluginManager")


@dataclasses.dataclass()
class NyxPluginRegistryEntry:
    """Plugin registry entry

    Attributes:
        plugin_cls: plugin class
        plugin_instance: initialized plugin plugin instance
    """

    plugin_cls: type[NyxPluginInterface] = dataclasses.field(default=None)
    plugin_instance: NyxPluginInterface = dataclasses.field(init=False, default=None)

    def initialize(self):
        """Call plugin initialize method and store resulting instance."""
        self.plugin_instance = self.plugin_cls.initialize()


class NyxPluginManager:
    """Central class for handling plugin registration, loading and initialization.

    Is not meant to be initialized outside of this module.
    Instead run the following code to get the instance:

    ```python
    from nyx.api.v1 import plugin_manager
    ```
    """

    def __init__(self):
        """Initialize manager instance"""
        self._registry: OrderedDict[str, NyxPluginRegistryEntry] = OrderedDict()
        self._loader = NyxPluginLoader()

    def register_plugin(self) -> Callable[[NyxPluginInterface], NyxPluginInterface]:
        """Decorator for plugin registration

        Returns:
            Decorator function


        Example:
            ```python
            from nyx.api.v1 import plugin_manager

            @plugin_manager.register_plugin()
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
                self.validate_plugin_class(plugin_cls)
            except Exception:
                LOGGER.exception("Failed to register %s", plugin_cls.__name__)
                return plugin_cls

            self._registry[plugin_cls.NAME] = NyxPluginRegistryEntry(
                plugin_cls=plugin_cls
            )
            return plugin_cls

        return _register_plugin_inner

    def validate_plugin_class(self, plugin_cls: NyxPluginInterface) -> None:
        if not plugin_cls.NAME:
            raise ValueError("Plugin has no NAME defined")

        if plugin_cls.NAME in self._registry:
            raise ValueError(
                f"Plugin with name {plugin_cls.NAME} already exists:"
                f"{self._registry[plugin_cls.NAME]}"
            )

    def get_plugin(self, name: str) -> NyxPluginRegistryEntry | None:
        """Get plugin registry entry by name.

        Args:
            name: plugin name

        Returns:
            Plugin registry entry
        """
        return self._registry.get(name)

    def iter_register(self) -> Iterator[tuple[str, NyxPluginRegistryEntry]]:
        """Iterate over plugin register dictionary.

        Yields:
            Plugin name and registry entry
        """
        yield from self._registry.items()

    def iter_plugin_entries(self) -> Iterator[NyxPluginRegistryEntry]:
        """Iterate over plugin registry entries

        Yields:
            Plugin registry entry
        """
        yield from self._registry.values()

    def initialize_plugins(self):
        """Iterate over registry and initialize each plugin."""
        if not self._registry:
            self._loader.load_plugins_from_paths()

        for plugin_entry in self.iter_plugin_entries():
            plugin_entry.initialize()
            LOGGER.info(f"Initialized plugin: {plugin_entry.plugin_cls.NAME}")
            LOGGER.debug(plugin_entry.plugin_instance.contents)


# Created once here - everyone who imports this module gets the same object.
plugin_manager = NyxPluginManager()
