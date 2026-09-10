import logging
from collections import OrderedDict
from copy import deepcopy

from nyx.version import __version__
from nyx.core.plugin_subsystem.registry import NYX_REGISTRY


LOGGER = logging.getLogger(__name__)


class Serializable:
    METADATA = {}
    TRACK_NYX_VERSION = False
    REQUIRED_PLUGINS = []
    REQUIRED_PLUGINS_KEY = "required_plugins"
    NYX_VERSION_METADATA_KEY = "nyx_version"

    def serialize(self) -> OrderedDict:
        """Serialize object into an OrderedDict.

        Returns:
            OrderedDict: serialized data

        """
        data = OrderedDict()

        metadata = self.metadata
        if self.metadata:
            data["metadata"] = metadata
        if self.REQUIRED_PLUGINS:
            data[self.REQUIRED_PLUGINS_KEY] = self.REQUIRED_PLUGINS
        return data

    @property
    def metadata(self):
        metadata_copy = deepcopy(self.METADATA)
        if self.TRACK_NYX_VERSION:
            metadata_copy[self.NYX_VERSION_METADATA_KEY] = __version__
        return metadata_copy

    @staticmethod
    def collect_required_plugins(data: OrderedDict) -> set[str]:
        combined = set()

        def _walk(node):
            if isinstance(node, dict):
                for key, value in node.items():
                    if key == Serializable.REQUIRED_PLUGINS_KEY and isinstance(
                        value, list
                    ):
                        combined.update(value)
                    else:
                        _walk(value)
            elif isinstance(node, list):
                for item in node:
                    _walk(item)

        _walk(data)
        return combined

    def required_plugins_are_loaded(self, data: OrderedDict) -> tuple[bool, list[str]]:
        required_plugins = self.collect_required_plugins(data)
        if not required_plugins:
            return True, []
        if required_plugins.issubset(NYX_REGISTRY.plugins):
            LOGGER.debug(f"{self}: Required plugins are loaded: {required_plugins}")
            return True, []
        return False, required_plugins.difference(NYX_REGISTRY.plugins)

    def deserialize(self, data: OrderedDict):
        """Deserialize object from given data.

        Args:
            data (OrderedDict): object data.

        """
        status, missing_plugins = self.required_plugins_are_loaded(data)
        if not status:
            raise RuntimeError(
                f"Failed to deserialize {self} due to missing plugins: {missing_plugins}"
            )
