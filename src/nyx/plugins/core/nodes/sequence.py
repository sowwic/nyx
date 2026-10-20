from nyx.api.v1 import Node, CoreNodes, CoreNodeComponents


class SequenceNode(Node):
    """Flow node with one input and several outputs."""

    DEFAULT_NAME = "sequence"
    DEFAULT_OUTPUTS_COUNT = 4

    @classmethod
    def get_type_id(cls) -> str:
        """str: node type id."""
        return CoreNodes.SEQUENCE

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return "Sequence"

    @classmethod
    def get_type_icon(cls) -> str:
        """str: resource path of the type icon."""
        return ":/core/icons/sequence_node"

    @classmethod
    def get_tags(cls) -> set[str]:
        """set[str]: node tags."""
        return {"logic"}

    def setup(self):
        """Add the flow components: one input and the outputs."""
        for output_index in range(4):
            flow_cpnt = self.components_model.create_component(CoreNodeComponents.FLOW)
            flow_cpnt.name = f"flow_{output_index}"
            flow_cpnt.writable = output_index == 0
            flow_cpnt.readable = True
            self.components_model.add_component(flow_cpnt)
