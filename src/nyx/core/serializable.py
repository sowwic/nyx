import logging
from collections import OrderedDict
from copy import deepcopy

from nyx.version import __version__
from nyx.core.plugin_subsystem.registry import NYX_REGISTRY


LOGGER = logging.getLogger(__name__)


class Serializable:
    METADATA: dict[str, str] = {}
    TRACK_NYX_VERSION: bool = False
    REQUIRED_PLUGINS: set[str] = set()
    REQUIRED_PLUGINS_KEY: str = "required_plugins"
    NYX_VERSION_METADATA_KEY: str = "nyx_version"

    @property
    def metadata(self):
        metadata_copy = deepcopy(self.METADATA)
        if self.TRACK_NYX_VERSION:
            metadata_copy[self.NYX_VERSION_METADATA_KEY] = __version__
        return metadata_copy

    def required_plugins_are_loaded(self, data: OrderedDict) -> tuple[bool, list[str]]:
        """Check if required plugins are loaded for serialized item data.

        Args:
            data: serialized item data

        Returns:
            Loaded Status and list of missing plugins
        """
        required_plugins = set(data.get(self.REQUIRED_PLUGINS_KEY, []))
        if not required_plugins:
            return True, []
        if required_plugins.issubset(NYX_REGISTRY.plugins):
            return True, []
        return False, required_plugins.difference(NYX_REGISTRY.plugins)

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
            data[self.REQUIRED_PLUGINS_KEY] = list(self.REQUIRED_PLUGINS)
        return data

    def deserialize(self, data: OrderedDict):
        """Deserialize object from given data.

        Args:
            data (OrderedDict): object data.

        """
        if isinstance(data, dict):
            status, missing_plugins = self.required_plugins_are_loaded(data)
            if not status:
                raise RuntimeError(
                    f"Failed to deserialize {self}"
                    f"due to missing plugins: {missing_plugins}"
                )
