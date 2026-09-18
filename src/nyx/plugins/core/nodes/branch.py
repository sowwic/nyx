from nyx.api.v1 import Node, CoreNodes, CoreNodeComponents


class BranchNode(Node):
    DEFAULT_NAME = "branch"
    REQUIRED_PLUGINS = {"NyxCore"}

    @classmethod
    def get_type_id(cls) -> str:
        return CoreNodes.BRANCH

    @classmethod
    def get_type_display_name(cls) -> str:
        return "Branch"

    @classmethod
    def get_tags(cls) -> set[str]:
        return {"logic"}

    def setup(self):
        self.flow_in = self.components_model.create_component(
            type_id=CoreNodeComponents.FLOW
        )
        self.flow_out_true = self.components_model.create_component(
            type_id=CoreNodeComponents.FLOW
        )
        self.flow_out_false = self.components_model.create_component(
            type_id=CoreNodeComponents.FLOW
        )
        self.value_cpnt = self.components_model.create_component(
            type_id=CoreNodeComponents.VALUE
        )

        self.flow_in.name = "flow_in"
        self.flow_in.is_writable = True

        self.flow_out_true.name = "flow_out_true"
        self.flow_out_true.is_readable = True
        self.flow_out_false.name = "flow_out_false"
        self.flow_out_false.is_readable = True

        self.value_cpnt.is_writable = True
        self.value_cpnt.value = True

        self.components_model.add_component(self.flow_in)
        self.components_model.add_component(self.flow_out_true)
        self.components_model.add_component(self.flow_out_false)
        self.components_model.add_component(self.value_cpnt)

    def execute_components(self):
        self.flow_out_true.is_active = self.value_cpnt.value
        self.flow_out_false.is_active = not self.value_cpnt.value
