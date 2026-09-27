from nyx.api.v1 import Node, CoreNodes, CoreNodeComponents


class FlowStartNode(Node):
    DEFAULT_NAME = "start"
    REQUIRED_PLUGINS = {"NyxCore"}

    @classmethod
    def get_type_id(cls) -> str:
        return CoreNodes.FLOW_START

    @classmethod
    def get_type_display_name(cls) -> str:
        return "Flow Start"

    @classmethod
    def get_tags(cls) -> set[str]:
        return {"logic"}

    def setup(self):
        self.flow_cpnt = self.components_model.create_component(CoreNodeComponents.FLOW)
        self.flow_cpnt.produces_output = True
        self.flow_cpnt.name = "flow"
        self.components_model.add_component(self.flow_cpnt)
