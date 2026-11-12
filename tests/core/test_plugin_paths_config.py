import pathlib

from nyx.core.layered_config import get_app_config
from nyx.core.plugin_subsystem.plugin_loader import NyxPluginLoader


def test_config_plugin_paths_are_added_to_source_paths(tmp_path: pathlib.Path):
    config = get_app_config()
    original = config.values.plugin_paths
    config.values.plugin_paths = [str(tmp_path)]
    try:
        loader = NyxPluginLoader()
    finally:
        config.values.plugin_paths = original
    assert tmp_path in loader.plugin_source_paths
