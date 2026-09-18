from nyx.api.v1 import NodeComponent, CoreNodeComponents


class ValueComponent(NodeComponent):
    TYPE_ID = CoreNodeComponents.VALUE
    DEFAULT_NAME = "value"
    REQUIRED_PLUGINS = {"NyxCore"}
    TAGS = {"value"}
