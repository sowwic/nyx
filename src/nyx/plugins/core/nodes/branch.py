from nyx.api.v1 import Node


class BranchNode(Node):
    TYPE_ID = "branch"
    REQUIRED_PLUGINS = ["NyxCore"]

    def setup(self):
        self.flow_cpnt = self.components_model.create_component("core:flow")
        self.value_cpnt = self.components_model.create_component("core:value")

        self.components_model.add_component(self.flow_cpnt)
        self.components_model.add_component(self.value_cpnt)
