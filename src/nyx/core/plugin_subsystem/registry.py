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
    from ..datatypes.datatype import Datatype


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
    """Registry of loaded plugins and the nodes, components and QML roots they provide.

    Attributes:
        plugins: plugin entries by type id
        node_components: component classes by type id
        nodes: node classes by type id
        datatypes: datatypes by type id
        qml_import_root_directories: QML import roots of registered plugins
    """

    plugins: OrderedDict[str, NyxPluginRegistryEntry] = dataclasses.field(
        init=False, default_factory=OrderedDict
    )
    node_components: OrderedDict[str, type[NodeComponent]] = dataclasses.field(
        init=False, default_factory=OrderedDict
    )
    nodes: OrderedDict[str, type[Node]] = dataclasses.field(
        init=False, default_factory=OrderedDict
    )
    datatypes: OrderedDict[str, Datatype] = dataclasses.field(
        init=False, default_factory=OrderedDict
    )
    qml_import_root_directories: list[pathlib.Path] = dataclasses.field(
        init=False, default_factory=list
    )

    def __post_init__(self):
        """Register the built-in QML import root."""
        self.register_qml_import_root_directory(QML_DIR)

    def clear(self):
        """Remove everything from the registry."""
        self.nodes.clear()
        self.node_components.clear()
        self.datatypes.clear()
        self.plugins.clear()
        self.qml_import_root_directories.clear()

    def get_plugin(self, name: str) -> NyxPluginRegistryEntry | None:
        """Get plugin registry entry by name.

        Args:
            name: plugin name

        Returns:
            Plugin registry entry
        """
        return self.plugins.get(name)

    def get_node_component_cls(self, type_id: str) -> type[NodeComponent]:
        """Get a component class.

        Args:
            type_id (str): component type id.

        Returns:
            type[NodeComponent] | None: class, None if not registered.
        """
        return self.node_components.get(type_id)

    def get_node_cls(self, type_id: str) -> type[Node]:
        """Get a node class.

        Args:
            type_id (str): node type id.

        Returns:
            type[Node] | None: class, None (and an error is logged) if not registered.
        """
        try:
            return self.nodes[type_id]
        except KeyError:
            LOGGER.error(
                f"Invalid node type_id: {type_id}\nAvailable Types: {self.nodes.keys()}"
            )

    def add_plugin(self, plugin_cls: NyxPlugin):
        """Add a plugin class to the registry.

        Args:
            plugin_cls (NyxPlugin): plugin class.
        """
        registry_entry = NyxPluginRegistryEntry(plugin_cls=plugin_cls)
        self.plugins[plugin_cls.get_type_id()] = registry_entry

    def register_plugin_content(self):
        """Rebuild the node and component registries from enabled plugins."""
        self.nodes.clear()
        self.node_components.clear()
        self.datatypes.clear()
        self.register_core_datatypes()

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
            self.register_datatypes(plugin_entry)
            self.register_qml_import_root(plugin_entry)

    def register_node_components(self, plugin_entry: NyxPluginRegistryEntry):
        """Register the components provided by a plugin. Duplicate type ids are skipped.

        Args:
            plugin_entry (NyxPluginRegistryEntry): initialized plugin entry.
        """
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
        """Register the nodes provided by a plugin. Duplicate type ids are skipped.

        Args:
            plugin_entry (NyxPluginRegistryEntry): initialized plugin entry.
        """
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

    def register_core_datatypes(self):
        """Register the built-in datatypes, which exist whatever plugins are enabled."""
        from ..datatypes.core_types import CORE_DATATYPES

        for datatype in CORE_DATATYPES:
            self.datatypes[datatype.type_id] = datatype

    def register_datatypes(self, plugin_entry: NyxPluginRegistryEntry):
        """Register the datatypes provided by a plugin. Duplicate type ids are skipped.

        Args:
            plugin_entry (NyxPluginRegistryEntry): initialized plugin entry.
        """
        LOGGER.debug("Registering new datatypes...")
        for datatype in plugin_entry.plugin_instance.contents.datatypes:
            if datatype.type_id in self.datatypes:
                LOGGER.error(
                    "Failed to register datatype %s - already registered",
                    datatype.type_id,
                )
                continue

            self.datatypes[datatype.type_id] = datatype
            LOGGER.debug(
                "Registered datatype %s from %s",
                datatype.type_id,
                plugin_entry.plugin_cls.get_type_id(),
            )

    def get_datatype(self, type_id: str) -> Datatype | None:
        """Get a datatype.

        Args:
            type_id (str): datatype type id.

        Returns:
            Datatype | None: datatype, None if not registered.
        """
        return self.datatypes.get(type_id)

    def resolve_datatype(self, type_id: str | None) -> Datatype:
        """Get a datatype, falling back to the object datatype.

        Args:
            type_id (str | None): datatype type id.

        Returns:
            Datatype: registered datatype, `OBJECT_DATATYPE` for missing or unknown
                ids (e.g. provided by a plugin that isn't loaded).
        """
        from ..datatypes.datatype import OBJECT_DATATYPE

        if not type_id:
            return OBJECT_DATATYPE
        datatype = self.datatypes.get(type_id)
        if datatype is None:
            LOGGER.warning("Unknown datatype %s, using object", type_id)
            return OBJECT_DATATYPE
        return datatype

    def infer_datatype(self, value: typing.Any) -> Datatype:
        """Get the datatype of a value.

        Args:
            value (typing.Any): value to find the datatype of.

        Returns:
            Datatype: first registered datatype matching the value,
                `OBJECT_DATATYPE` if there is none.
        """
        from ..datatypes.datatype import OBJECT_DATATYPE

        for datatype in self.datatypes.values():
            if datatype.matches(value):
                return datatype
        return OBJECT_DATATYPE

    def find_datatype_for_type(self, python_type: type) -> Datatype | None:
        """Find the datatype of a python type.

        Args:
            python_type (type): python type, e.g. from a type hint.

        Returns:
            Datatype | None: first registered datatype of exactly that type, None if
                there is none.
        """
        for datatype in self.datatypes.values():
            if datatype.python_type is python_type:
                return datatype
        return None

    def iter_datatypes(self) -> Iterator[Datatype]:
        """Iterate registered datatypes.

        Yields:
            Datatype: registered datatype.
        """
        yield from self.datatypes.values()

    def register_qml_import_root_directory(
        self, import_root_directory: pathlib.Path
    ) -> bool:
        """Register a QML import root.

        Args:
            import_root_directory (pathlib.Path): directory to register.

        Returns:
            bool: directory was newly registered.
        """
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
        """Register the QML directory of a plugin.

        Args:
            plugin_entry (NyxPluginRegistryEntry): plugin entry.
        """
        qml_directory = plugin_entry.plugin_cls.qml_directory()
        if qml_directory is None:
            return
        self.register_qml_import_root_directory(qml_directory)

    def resolve_qml_source(
        self, qml_module_uri: str, qml_type_name: str
    ) -> pathlib.Path:
        """Find a QML file in the registered import roots.

        Args:
            qml_module_uri (str): dotted QML module uri.
            qml_type_name (str): QML type name, without extension.

        Returns:
            pathlib.Path: QML file path.

        Raises:
            FileNotFoundError: if no root contains the file.
        """
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
        """Iterate registered components.

        Yields:
            tuple[str, type[NodeComponent]]: type id and class.
        """
        yield from self.node_components.items()

    def get_plugins_types_dict(self) -> OrderedDict:
        """Get plugin classes by type id.

        Returns:
            OrderedDict: plugin classes.
        """
        flat_dict = OrderedDict()
        for type_id, registry_entry in self.iter_plugins():
            flat_dict[type_id] = registry_entry.plugin_cls
        return flat_dict


NYX_REGISTRY = NyxRegistry()
