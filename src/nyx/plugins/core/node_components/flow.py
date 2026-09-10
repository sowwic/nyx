from nyx.api.v1 import NodeComponent


class FlowComponent(NodeComponent):
    TYPE_ID = "flow"
    REQUIRED_PLUGINS = ["NyxCore"]
