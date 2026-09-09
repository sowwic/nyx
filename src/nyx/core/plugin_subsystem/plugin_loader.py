import pathlib
import logging
import sys

import os
import importlib.util
from importlib.machinery import ModuleSpec


LOGGER = logging.getLogger("NyxPluginLoader")

NYX_PLUGIN_PATHS_ENV_VAR = "NYX_PLUGIN_PATH"
NYX_PLUGIN_PATHS_ENV_SEPARATOR = os.pathsep  # ':' on Linux/macOS, ';' on Windows


class NyxPluginLoader:
    """Class for discovering and loading plugins from given directories.

    Attributes:
        NYX_PLUGIN_FILE: plugin entry point file name.
    """

    NYX_PLUGIN_FILE = "nyx_plugin.py"

    def __init__(self, plugin_source_paths: list[pathlib.Path] | None = None):
        """Initialize loader instance.

        Args:
            plugin_source_paths: optional paths override.
            If not provided will default to built-in + `NYX_PLUGIN_PATH` env variable
        """
        if plugin_source_paths is None:
            plugin_source_paths = [
                self._builtin_plugins_path(),
                *self._env_plugin_paths(),
            ]
        self.plugin_source_paths = plugin_source_paths

    @staticmethod
    def _builtin_plugins_path() -> pathlib.Path:
        """Get path for built-in plugins directory.

        Returns:
            Nyx plugins directory path.

        Raises:
            ValueError: Built-in directory is missing.
        """
        spec: ModuleSpec = importlib.util.find_spec("nyx.plugins")
        if spec.submodule_search_locations is None:
            raise ValueError("No path found for builtt-in plugins")
        return pathlib.Path(spec.submodule_search_locations[0])

    @staticmethod
    def _env_plugin_paths() -> list[pathlib.Path]:
        """Get paths from environment variable.

        Returns:
            Additional plugin paths.
        """
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

    def load_plugin(self, plugin_file: pathlib.Path | str):
        # TODO: Break down into smaller methods
        # TODO: Doctring
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

    def find_plugins_in_dir(self, root_path: pathlib.Path | str) -> list[pathlib.Path]:
        """Recursively find plugins entry points in given directories

        Args:
            root_path: directory to scan

        Returns:
            Plugins entry points
        """
        root_path = pathlib.Path(root_path)
        return list(root_path.rglob(self.NYX_PLUGIN_FILE))

    def collect_plugins_from_paths(self) -> list[pathlib.Path]:
        """Find plugins from loader source paths.

        Returns:
            Plugins entry points
        """
        result = []
        for plugin_dir in self.plugin_source_paths:
            plugin_files = self.find_plugins_in_dir(plugin_dir)
            if not plugin_files:
                LOGGER.warning("No plugins found for path: $s", plugin_dir.as_posix())
                continue
            result.extend(plugin_files)
        LOGGER.debug(f"Collected plugin files: {result}")
        return result

    def load_plugins_from_paths(self):
        """Find and load plugins from loader source paths."""
        for plugin_dir in self.collect_plugins_from_paths():
            self.load_plugin(plugin_dir)
