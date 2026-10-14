import pathlib
import typing
import dataclasses
import logging
from collections import OrderedDict
from collections.abc import Iterator
from nyx.core.logger import NyxLogger
from nyx.static.paths import QML_DIR

if typing.TYPE_CHECKING:
    from .plugin import NyxPlugin
    from ..node import Node
    from ..node_component import NodeComponent


logging.setLoggerClass(NyxLogger)
LOGGER = logging.getLogger("NyxRegistry")


@dataclasses.dataclass()
class NyxPluginRegistryEntry:
    """Plugin registry entry

    Attributes:
        plugin_cls: plugin class
        plugin_instance: initialized plugin plugin instance
    """

    enabled: bool = True
    plugin_cls: type[NyxPlugin] = dataclasses.field(default=None)
    plugin_instance: NyxPlugin | None = dataclasses.field(init=False, default=None)

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
    qml_import_root_directories: list[pathlib.Path] = dataclasses.field(
        init=False, default_factory=list
    )

    def __post_init__(self):
        self.register_qml_import_root_directory(QML_DIR)

    def clear(self):
        self.nodes.clear()
        self.node_components.clear()
        self.plugins.clear()
        self.qml_source_directories.clear()

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
        try:
            return self.nodes[type_id]
        except KeyError:
            LOGGER.error(
                f"Invalid node type_id: {type_id}\nAvailable Types: {self.nodes.keys()}"
            )

    def add_plugin(self, plugin_cls: NyxPlugin):
        registry_entry = NyxPluginRegistryEntry(plugin_cls=plugin_cls)
        self.plugins[plugin_cls.get_type_id()] = registry_entry

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
                    f"Skipping disabled plugin {plugin_entry.plugin_cls.get_type_id()}"
                )
                continue

            self.register_node_components(plugin_entry)
            self.register_nodes(plugin_entry)
            self.register_qml_import_root(plugin_entry)

    def register_node_components(self, plugin_entry: NyxPluginRegistryEntry):
        LOGGER.debug("Registering new node components...")
        for node_component_cls in plugin_entry.plugin_instance.contents.node_components:
            if node_component_cls.get_type_id() in self.node_components:
                LOGGER.error(
                    (
                        "Failed to register component class %s - "
                        "TYPE_ID %s is already registered as %s"
                    ),
                    node_component_cls.__name__,
                    node_component_cls.get_type_id(),
                    self.node_components[node_component_cls.get_type_id()],
                )
                continue

            self.node_components[node_component_cls.get_type_id()] = node_component_cls
            node_component_cls.SOURCE_PLUGIN = plugin_entry
            LOGGER.debug(
                "Registered node component: %s (%s) from %s",
                node_component_cls.get_type_id(),
                node_component_cls.__name__,
                plugin_entry.plugin_cls.get_type_id(),
            )

    def register_nodes(self, plugin_entry: NyxPluginRegistryEntry):
        LOGGER.debug("Registering new nodes...")
        for node_cls in plugin_entry.plugin_instance.contents.nodes:
            if node_cls.get_type_id() in self.nodes:
                LOGGER.error(
                    (
                        "Failed to register node class %s - "
                        "TYPE_ID %s is already registered as %s"
                    ),
                    node_cls.__name__,
                    node_cls.get_type_id(),
                    self.nodes[node_cls.get_type_id()],
                )
                continue

            self.nodes[node_cls.get_type_id()] = node_cls
            node_cls.SOURCE_PLUGIN = plugin_entry
            LOGGER.debug(
                "Registered node %s (%s) from %s",
                node_cls.get_type_id(),
                node_cls.__name__,
                plugin_entry.plugin_cls.get_type_id(),
            )

    def register_qml_import_root_directory(
        self, import_root_directory: pathlib.Path
    ) -> bool:
        resolved_import_root_directory = import_root_directory.resolve()
        if not resolved_import_root_directory.is_dir():
            LOGGER.warning(
                "QML import root is not a directory: %s",
                resolved_import_root_directory.as_posix(),
            )
            return False

        if resolved_import_root_directory in self.qml_import_root_directories:
            return False

        LOGGER.debug(
            "Registering QML import root: %s", resolved_import_root_directory.as_posix()
        )
        self.qml_import_root_directories.append(resolved_import_root_directory)
        return True

    def register_qml_import_root(self, plugin_entry: NyxPluginRegistryEntry):
        qml_directory = plugin_entry.plugin_cls.qml_directory()
        if qml_directory is None:
            return
        self.register_qml_import_root_directory(qml_directory)

    def resolve_qml_source(
        self, qml_module_uri: str, qml_type_name: str
    ) -> pathlib.Path:
        module_relative_directory = pathlib.Path(*qml_module_uri.split("."))
        for import_root_directory in self.qml_import_root_directories:
            candidate_qml_file_path = (
                import_root_directory
                / module_relative_directory
                / f"{qml_type_name}.qml"
            )
            if candidate_qml_file_path.is_file():
                return candidate_qml_file_path
        raise FileNotFoundError(
            f"No QML file for {qml_module_uri}.{qml_type_name} in registered roots: "
            f"{self.qml_import_root_directories}"
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

    def get_plugins_types_dict(self) -> OrderedDict:
        flat_dict = OrderedDict()
        for type_id, registry_entry in self.iter_plugins():
            flat_dict[type_id] = registry_entry.plugin_cls
        return flat_dict


NYX_REGISTRY = NyxRegistry()
