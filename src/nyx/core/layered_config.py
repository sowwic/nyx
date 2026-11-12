from json_config.api import ConfigLayer, LayeredConfig
from PySide6 import QtCore

from nyx.core.config_values.root_values import NyxConfigValues
from nyx.static.paths import USER_CONFIG_FILE_PATH


class NyxConfig(LayeredConfig[NyxConfigValues]):
    """Nyx layered config.

    Attributes:
        VALUES_CLASS: ConfigValues class to be used with this config
        ROOT_CONFIG_LAYER: Root config layer
    """

    NAME = "general"
    VALUES_CLASS = NyxConfigValues
    ROOT_CONFIG_LAYER = ConfigLayer(name="user", file_path=USER_CONFIG_FILE_PATH)

    def __init__(self):
        """Initialize NyxConfig, registering the root config layer."""
        super().__init__(layer_filter=self.ROOT_CONFIG_LAYER.name)
        self._register_root_layer()

    def _register_root_layer(self):
        """Register the root config layer unless already registered."""
        if self.ROOT_CONFIG_LAYER.name not in self.layer_manager.root_layers:
            self.layer_manager.register(self.ROOT_CONFIG_LAYER)


def get_app_config() -> NyxConfig:
    """Get the config of the running application.

    Returns:
        NyxConfig: config the application loaded at startup, so it has the values of
            the user's config file. Without an application a new config is created and
            resolved.
    """
    config = getattr(QtCore.QCoreApplication.instance(), "config", None)
    if config is None:
        config = NyxConfig()
        config.resolve()
    return config
