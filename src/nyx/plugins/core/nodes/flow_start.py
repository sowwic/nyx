from nyx.api.v1 import Node, CoreNodes, CoreNodeComponents


class FlowStartNode(Node):
    """Node marking where the execution flow of its parent scope begins."""

    DEFAULT_NAME = "start"

    @classmethod
    def get_type_id(cls) -> str:
        """str: node type id."""
        return CoreNodes.FLOW_START

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return "Flow Start"

    @classmethod
    def get_type_icon(cls) -> str:
        """str: resource path of the type icon."""
        return ":/core/icons/flow_start_node"

    @classmethod
    def get_tags(cls) -> set[str]:
        """set[str]: node tags."""
        return {"logic"}

    def setup(self):
        """Add the flow output component."""
        self.flow_cpnt = self.components_model.create_component(CoreNodeComponents.FLOW)
        self.flow_cpnt.produces_output = True
        self.flow_cpnt.name = "flow"
        self.components_model.add_component(self.flow_cpnt)
