from nyx.api.v1 import Node, CoreNodes, CoreNodeComponents


class FlowStartNode(Node):
    TYPE_ID = CoreNodes.FLOW_START
    DEFAULT_NAME = "start"
    REQUIRED_PLUGINS = {"NyxCore"}
    TAGS = {"logic"}

    def setup(self):
        self.flow_cpnt = self.components_model.create_component(CoreNodeComponents.FLOW)
        self.flow_cpnt.is_readable = True
        self.components_model.add_component(self.flow_cpnt)
