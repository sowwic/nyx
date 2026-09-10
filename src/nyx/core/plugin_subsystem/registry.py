import typing
import dataclasses
import logging
from collections import OrderedDict
from collections.abc import Iterator

if typing.TYPE_CHECKING:
    from .plugin_interface import NyxPluginInterface
    from ..node import Node
    from ..node_component._base_component import NodeComponent


LOGGER = logging.getLogger("NyxRegistry")


@dataclasses.dataclass()
class NyxPluginRegistryEntry:
    """Plugin registry entry

    Attributes:
        plugin_cls: plugin class
        plugin_instance: initialized plugin plugin instance
    """

    enabled: bool = True
    plugin_cls: type[NyxPluginInterface] = dataclasses.field(default=None)
    plugin_instance: NyxPluginInterface = dataclasses.field(init=False, default=None)

    def initialize(self):
        """Call plugin initialize method and store resulting instance."""
        self.plugin_instance = self.plugin_cls.initialize()


@dataclasses.dataclass()
class NyxRegistry:
    plugins: OrderedDict[str, NyxPluginRegistryEntry] = dataclasses.field(
        init=False, default_factory=OrderedDict
    )
    node_components: OrderedDict[str, type[NodeComponent]] = dataclasses.field(
        init=False, default_factory=OrderedDict
    )
    nodes: OrderedDict[str, type[Node]] = dataclasses.field(
        init=False, default_factory=OrderedDict
    )

    def clear(self):
        self.nodes.clear()
        self.node_components.clear()
        self.plugins.clear()

    def get_plugin(self, name: str) -> NyxPluginRegistryEntry | None:
        """Get plugin registry entry by name.

        Args:
            name: plugin name

        Returns:
            Plugin registry entry
        """
        return self.plugins.get(name)

    def get_node_component_cls(self, type_id: str) -> type[NodeComponent]:
        return self.node_components.get(type_id)

    def get_node_cls(self, type_id: str) -> type[Node]:
        return self.nodes.get(type_id)

    def add_plugin(self, plugin_cls: NyxPluginInterface):
        registry_entry = NyxPluginRegistryEntry(plugin_cls=plugin_cls)
        self.plugins[plugin_cls.NAME] = registry_entry

    def register_plugin_content(self):
        self.nodes.clear()
        self.node_components.clear()

        for plugin_entry in self.iter_plugin_entries():
            if not plugin_entry.plugin_instance:
                LOGGER.warning(
                    f"Can't scan components for not initialized plugin: {plugin_entry}"
                )
                continue

            if not plugin_entry.enabled:
                LOGGER.warning(
                    f"Skipping disabled plugin {plugin_entry.plugin_cls.NAME}"
                )
                continue

            self.register_node_components(plugin_entry)
            self.register_nodes(plugin_entry)

    def register_node_components(self, plugin_entry: NyxPluginRegistryEntry):
        for node_component_cls in plugin_entry.plugin_instance.contents.node_components:
            if node_component_cls.TYPE_ID in self.node_components:
                LOGGER.error(
                    "Failed to register component class %s - TYPE_ID %s is already registered as %s",
                    node_component_cls.__name__,
                    node_component_cls.TYPE_ID,
                    self.node_components[node_component_cls.TYPE_ID],
                )
                continue

            self.node_components[node_component_cls.TYPE_ID] = node_component_cls
            LOGGER.debug(
                "Registered node component: %s(%s) from %s",
                node_component_cls.TYPE_ID,
                node_component_cls.__name__,
                plugin_entry.plugin_cls.NAME,
            )

    def register_nodes(self, plugin_entry: NyxPluginRegistryEntry):
        for node_cls in plugin_entry.plugin_instance.contents.nodes:
            if node_cls.TYPE_ID in self.nodes:
                LOGGER.error(
                    "Failed to register node class %s - TYPE_ID %s is already registered as %s",
                    node_cls.__name__,
                    node_cls.TYPE_ID,
                    self.nodes[node_cls.TYPE_ID],
                )
                continue

            self.nodes[node_cls.TYPE_ID] = node_cls
            LOGGER.debug(
                "Registered node %s(%s) from %s",
                node_cls.TYPE_ID,
                node_cls.__name__,
                plugin_entry.plugin_cls.NAME,
            )

    def iter_plugins(self) -> Iterator[tuple[str, NyxPluginRegistryEntry]]:
        """Iterate over plugin register dictionary.

        Yields:
            Plugin name and registry entry
        """
        yield from self.plugins.items()

    def iter_plugin_entries(self) -> Iterator[NyxPluginRegistryEntry]:
        """Iterate over plugin registry entries

        Yields:
            Plugin registry entry
        """
        yield from self.plugins.values()

    def iter_node_components(self) -> Iterator[tuple[str, type[NodeComponent]]]:
        yield from self.node_components.items()


NYX_REGISTRY = NyxRegistry()
