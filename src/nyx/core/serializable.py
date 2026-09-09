from collections import OrderedDict
from copy import deepcopy

from nyx.version import __version__


class Serializable:
    METADATA = {}
    TRACK_NYX_VERSION = False

    def serialize(self) -> OrderedDict:
        """Serialize object into an OrderedDict.

        Returns:
            OrderedDict: serialized data

        """
        data = OrderedDict()

        metadata = self.metadata
        if self.metadata:
            data["metadata"] = metadata
        return data

    @property
    def metadata(self):
        metadata_copy = deepcopy(self.METADATA)
        if self.TRACK_NYX_VERSION:
            metadata_copy["nyx_version"] = __version__
        return metadata_copy

    def deserialize(self, data: OrderedDict):
        """Deserialize object from given data.

        Args:
            data (OrderedDict): object data.

        """
        ...
