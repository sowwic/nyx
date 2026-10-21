from nyx.api.v1 import Node, CoreNodes, CoreNodeComponents


class ActionNode(Node):
    """Flow node with a flow input and output, running its components when executed."""

    DEFAULT_NAME = "action"

    @classmethod
    def get_type_id(cls) -> str:
        """str: node type id."""
        return CoreNodes.ACTION

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return "Action"

    @classmethod
    def get_type_icon(cls) -> str:
        """str: resource path of the type icon."""
        return ":/core/icons/action_node"

    @classmethod
    def get_description(cls) -> str:
        """str: what the node type does, shown in the palette."""
        return "Runs its components when the flow reaches it. A general purpose step with a flow input and output."

    @classmethod
    def get_tags(cls) -> set[str]:
        """set[str]: node tags."""
        return {"common"}

    def setup(self):
        """Add the flow component."""
        self.flow_cpnt = self.components_model.create_component(CoreNodeComponents.FLOW)
        self.flow_cpnt.readable = True
        self.flow_cpnt.writable = True
        self.flow_cpnt.name = "flow"

        self.components_model.add_component(self.flow_cpnt)
