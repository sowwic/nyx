import functools
from ..core.plugin_subsystem.plugin_manager import NyxPluginManager


def with_plugins(*names: str):
    def inner_with_plugins(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            plugin_manager = NyxPluginManager()
            plugin_manager.initialize_plugins(include=list(names))
            return func(*args, **kwargs)

        return wrapper

    return inner_with_plugins
