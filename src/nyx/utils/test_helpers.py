import functools
import typing
from ..core.plugin_subsystem.plugin_manager import NyxPluginManager


def with_plugins(*names: str) -> typing.Callable:
    """Decorator: Run given function with only specified plugins initialized.

    Args:
        names: plugin names to initialize

    Returns:
        decorated function
    """

    def inner_with_plugins(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            plugin_manager = NyxPluginManager()
            plugin_manager.initialize_plugins(include=list(names))
            return func(*args, **kwargs)

        return wrapper

    return inner_with_plugins
