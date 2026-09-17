from nyx.api.v1 import Node, CoreNodes, CoreNodeComponents


class ActionNode(Node):
    TYPE_ID = CoreNodes.ACTION
    REQUIRED_PLUGINS = ["NyxCore"]
    DEFAULT_NAME = "action"
    TAGS = ["general"]

    def setup(self):
        self.flow_cpnt = self.components_model.create_component(CoreNodeComponents.FLOW)
        self.flow_cpnt.is_readable = True
        self.flow_cpnt.is_writable = True
        self.flow_cpnt.name = "flow"

        self.components_model.add_component(self.flow_cpnt)

    def execute_components(self):
        pass
