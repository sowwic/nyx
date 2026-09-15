from nyx.api.v1 import NodeComponent


class FlowComponent(NodeComponent):
    TYPE_ID = "core:flow"
    REQUIRED_PLUGINS = ["NyxCore"]
