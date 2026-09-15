from nyx.api.v1 import Node


class FlowStartNode(Node):
    TYPE_ID = "core:flow_start"
    REQUIRED_PLUGINS = ["NyxCore"]

    def setup(self):
        self.flow_cpnt = self.components_model.create_component("core:flow")

        self.components_model.add_component(self.flow_cpnt)
