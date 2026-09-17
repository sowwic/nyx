import pathlib

from nyx.api.v1 import NodeComponent


class FlowComponent(NodeComponent):
    TYPE_ID = "core:flow"
    DEFAULT_NAME = "flow"
    REQUIRED_PLUGINS = ["NyxCore"]
    TAGS = ["logic"]

    def serialize_value(self) -> str:
        if self.value:
            return str(self.value)
        return None

    def deserialize_value(self, value: str | None) -> pathlib.PurePosixPath | None:
        if value is None:
            return value
        return pathlib.PurePosixPath(value)
