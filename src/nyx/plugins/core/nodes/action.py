from nyx.api.v1 import Node, CoreNodes, CoreNodeComponents


class ActionNode(Node):
    DEFAULT_NAME = "action"
    REQUIRED_PLUGINS = {"NyxCore"}

    @classmethod
    def get_type_id(cls) -> str:
        return CoreNodes.ACTION

    @classmethod
    def get_type_display_name(cls) -> str:
        return "Action"

    @classmethod
    def get_tags(cls) -> set[str]:
        return {"common"}

    def setup(self):
        self.flow_cpnt = self.components_model.create_component(CoreNodeComponents.FLOW)
        self.flow_cpnt.is_readable = True
        self.flow_cpnt.is_writable = True
        self.flow_cpnt.name = "flow"

        self.components_model.add_component(self.flow_cpnt)

    def execute_components(self):
        pass
