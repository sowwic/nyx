from nyx.api.v1 import Node, CoreNodes, CoreNodeComponents


class SequenceNode(Node):
    DEFAULT_NAME = "sequence"
    DEFAULT_OUTPUTS_COUNT = 4

    @classmethod
    def get_type_id(cls) -> str:
        return CoreNodes.SEQUENCE

    @classmethod
    def get_type_display_name(cls) -> str:
        return "Sequence"

    @classmethod
    def get_type_icon(cls) -> str:
        return ":/core/icons/sequence_node"

    @classmethod
    def get_tags(cls) -> set[str]:
        return {"logic"}

    def setup(self):
        for output_index in range(4):
            flow_cpnt = self.components_model.create_component(CoreNodeComponents.FLOW)
            flow_cpnt.name = f"flow_{output_index}"
            flow_cpnt.accepts_input = output_index == 0
            flow_cpnt.produces_output = True
            self.components_model.add_component(flow_cpnt)
