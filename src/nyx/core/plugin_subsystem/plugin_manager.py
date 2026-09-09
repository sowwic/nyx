import sys
import logging
import os
import typing
import pathlib
import importlib.util
import dataclasses
from collections import OrderedDict
from collections.abc import Generator, Callable, Iterator

from .plugin_interface import NyxPluginInterface

if typing.TYPE_CHECKING:
    from importlib.machinery import ModuleSpec


LOGGER = logging.getLogger("NyxPluginManager")

NYX_PLUGIN_PATHS_ENV_VAR = "NYX_PLUGIN_PATHS"
NYX_PLUGIN_PATHS_ENV_SEPARATOR = os.pathsep  # ':' on Linux/macOS, ';' on Windows

PluginT = typing.TypeVar("PluginT")


@dataclasses.dataclass()
class NyxPluginRegistryEntry:
    plugin_cls: type[NyxPluginInterface] = dataclasses.field(default=None)
    plugin_instance: NyxPluginInterface = dataclasses.field(init=False, default=None)

    def initialize(self):
        self.plugin_instance = self.plugin_cls.initialize()


class NyxPluginManager:
    NYX_PLUGIN_FILE = "nyx_plugin.py"

    def __init__(self, plugin_source_paths: list[pathlib.Path] | None = None):
        self._registry: OrderedDict[str, NyxPluginRegistryEntry] = OrderedDict()

        if plugin_source_paths is None:
            plugin_source_paths = [
                self._builtin_plugins_path(),
                *self._env_plugin_paths(),
            ]
        self.plugin_source_paths = plugin_source_paths

    @staticmethod
    def _builtin_plugins_path() -> pathlib.Path:
        spec: ModuleSpec = importlib.util.find_spec("nyx.plugins")
        return pathlib.Path(spec.submodule_search_locations[0])

    @staticmethod
    def _env_plugin_paths() -> list[pathlib.Path]:
        raw_value = os.environ.get(NYX_PLUGIN_PATHS_ENV_VAR, "")
        if not raw_value:
            return []

        paths = [
            pathlib.Path(p) for p in raw_value.split(NYX_PLUGIN_PATHS_ENV_SEPARATOR) if p
        ]
        for each_path in paths:
            if not each_path.is_dir():
                LOGGER.warning(
                    "Plugin path from %s does not exist: %s",
                    NYX_PLUGIN_PATHS_ENV_VAR,
                    each_path,
                )
        return paths

    def find_plugins_in_dir(self, root_path: pathlib.Path | str) -> list[pathlib.Path]:
        root_path = pathlib.Path(root_path)
        return list(root_path.rglob(self.NYX_PLUGIN_FILE))

    def register_plugin(self) -> Callable[[NyxPluginInterface], NyxPluginInterface]:
        """Decorator: @plugin_manager.register_plugin("my_plugin")

        Args:
            name: plugin name

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

        def decorator(plugin_cls: NyxPluginInterface) -> NyxPluginInterface:
            if plugin_cls.NAME in self._registry:
                LOGGER.error(
                    f"Plugin with name {plugin_cls.NAME} already exists: {self._registry[plugin_cls.NAME]}"
                )
                return

            self._registry[plugin_cls.NAME] = NyxPluginRegistryEntry(
                plugin_cls=plugin_cls
            )
            return plugin_cls

        return decorator

    def unregister_plugin(self, name: str) -> None:
        if name not in self._registry:
            LOGGER.warning("Cannot unregister unknown plugin: %s", name)
            return
        del self._registry[name]

    def get_plugin(self, name: str) -> object | None:
        return self._registry.get(name)

    def iter_register(self) -> Iterator[tuple[str, NyxPluginRegistryEntry]]:
        yield from self._registry.items()

    def iter_plugin_entries(self) -> Iterator[NyxPluginRegistryEntry]:
        yield from self._registry.values()

    def load_plugin(self, plugin_file: pathlib.Path | str):
        LOGGER.info("Loading plugin from: %s", plugin_file)
        plugin_file = pathlib.Path(plugin_file)
        package_dir = plugin_file.parent
        package_name = package_dir.name

        module_spec: ModuleSpec = importlib.util.spec_from_file_location(
            name=f"{package_name}.{plugin_file.stem}",
            location=plugin_file,
            submodule_search_locations=[str(package_dir)],
        )
        module = importlib.util.module_from_spec(module_spec)

        # Register the parent package too, or relatives imports will still fail
        if package_name not in sys.modules:
            if (package_dir / "__init__.py").is_file():
                package_spec: ModuleSpec = importlib.util.spec_from_file_location(
                    package_name,
                    package_dir / "__init__.py",
                    submodule_search_locations=[str(package_dir)],
                )
            else:
                package_spec: ModuleSpec = importlib.util.spec_from_loader(
                    package_name, loader=None, is_package=True
                )
            package_module = importlib.util.module_from_spec(package_spec)
            package_module.__path__ = [str(package_dir)]
            sys.modules[package_name] = package_module

        sys.modules[module_spec.name] = module
        module_spec.loader.exec_module(module=module)

    def collect_plugins_from_paths(self):
        result = []
        for plugin_dir in self.plugin_source_paths:
            plugin_files = self.find_plugins_in_dir(plugin_dir)
            if not plugin_files:
                LOGGER.warning("No plugins found for path: $s", plugin_dir.as_posix())
            result.extend(plugin_files)
        return result

    def load_plugins_from_paths(self):
        for plugin_dir in self.collect_plugins_from_paths():
            self.load_plugin(plugin_dir)
            LOGGER.info(self._registry)

    def initialize_plugins(self):
        if not self._registry:
            self.load_plugins_from_paths()

        for plugin_entry in self.iter_plugin_entries():
            plugin_entry.initialize()
        LOGGER.info(self._registry)


# Created once here — everyone who imports this module gets the same object.
plugin_manager = NyxPluginManager()
