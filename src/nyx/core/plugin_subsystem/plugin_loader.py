import pathlib
import logging
import sys

import os
import importlib.util
from importlib.machinery import ModuleSpec

from ...utils.profiling import profile


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
                If not provided will default to the standard library plugin, the built-in
                plugins and the `NYX_PLUGIN_PATH` env variable paths
        """
        if plugin_source_paths is None:
            plugin_source_paths = [
                self._stdlib_path(),
                self._builtin_plugins_path(),
                *self._env_plugin_paths(),
            ]
        self.plugin_source_paths = plugin_source_paths

    @staticmethod
    def _stdlib_path() -> pathlib.Path:
        """Get path for the directory of the core plugin that others rely on.

        Returns:
            Nyx standard library directory path.

        Raises:
            ValueError: Standard library directory is missing.
        """
        spec: ModuleSpec = importlib.util.find_spec("nyx.stdlib")
        if spec is None or spec.submodule_search_locations is None:
            raise ValueError("No path found for the standard library plugin")
        return pathlib.Path(spec.submodule_search_locations[0])

    @staticmethod
    def _importable_module_name(plugin_file: pathlib.Path) -> str | None:
        """Get the module name of a plugin file that is part of the `nyx` package.

        Args:
            plugin_file: plugin entry point file path

        Returns:
            Dotted module name such as `nyx.stdlib.nyx_plugin`, None if the file isn't
            inside the package.
        """
        package_dir = pathlib.Path(
            importlib.util.find_spec("nyx").submodule_search_locations[0]
        ).resolve()
        try:
            relative = plugin_file.resolve().relative_to(package_dir)
        except ValueError:
            return None
        return ".".join(["nyx", *relative.with_suffix("").parts])

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
        """Load plugin from give plugin entry point file.

        This will register plugin file and

        Args:
            plugin_file: plugin entry point file path
        """
        LOGGER.info("Loading plugin from: %s", plugin_file)
        plugin_file = pathlib.Path(plugin_file)

        # Plugins of the package are imported by their real name, so that other
        # plugins importing from them get the same classes the registry holds.
        module_name = self._importable_module_name(plugin_file)
        if module_name is not None:
            importlib.import_module(module_name)
            return

        package_dir = plugin_file.parent
        package_name = package_dir.name

        loaded_module = sys.modules.get(f"{package_name}.{plugin_file.stem}")
        loaded_file = getattr(loaded_module, "__file__", None)
        if loaded_file and pathlib.Path(loaded_file).resolve() == plugin_file.resolve():
            LOGGER.debug("Plugin is already loaded: %s", plugin_file)
            return

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
                LOGGER.warning("No plugins found for path: %s", plugin_dir.as_posix())
                continue
            result.extend(plugin_files)
        LOGGER.debug(f"Collected plugin files: {result}")
        return result

    @profile(text="Plugins loaded in {seconds:.4f}s")
    def load_plugins_from_paths(self):
        """Find and load plugins from loader source paths."""
        collected_plugins_dirs = self.collect_plugins_from_paths()
        for plugin_dir in collected_plugins_dirs:
            self.load_plugin(plugin_dir)
        LOGGER.info(f"Total number of plugins: {len(collected_plugins_dirs)}")
