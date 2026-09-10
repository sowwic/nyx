from nyx.api.v1 import NodeComponent


class ValueComponent(NodeComponent):
    TYPE_ID = "value"
    REQUIRED_PLUGINS = ["NyxCore"]
