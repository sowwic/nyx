from nyx.api.v1 import NodeComponent, CoreNodeComponents


class ValueComponent(NodeComponent):
    TYPE_ID = CoreNodeComponents.VALUE
    REQUIRED_PLUGINS = ["NyxCore"]
    DEFAULT_NAME = "value"
    TAGS = ["value"]
