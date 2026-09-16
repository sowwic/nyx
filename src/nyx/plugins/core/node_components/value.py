from nyx.api.v1 import NodeComponent


class ValueComponent(NodeComponent):
    TYPE_ID = "core:value"
    REQUIRED_PLUGINS = ["NyxCore"]
    DEFAULT_NAME = "value"
    TAGS = ["value"]
