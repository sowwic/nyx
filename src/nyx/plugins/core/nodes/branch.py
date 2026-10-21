from nyx.api.v1 import Node, CoreNodes, CoreNodeComponents, CoreDatatypes


class BranchNode(Node):
    """Flow node continuing through its true or false output depending on a value."""

    DEFAULT_NAME = "branch"

    @classmethod
    def get_type_id(cls) -> str:
        """str: node type id."""
        return CoreNodes.BRANCH

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return "Branch"

    @classmethod
    def get_type_icon(cls) -> str:
        """str: resource path of the type icon."""
        return ":/core/icons/branch_node"

    @classmethod
    def get_description(cls) -> str:
        """str: what the node type does, shown in the palette."""
        return (
            "Continues through the true or false flow output depending on the "
            "condition value."
        )

    @classmethod
    def get_tags(cls) -> set[str]:
        """set[str]: node tags."""
        return {"logic"}

    def setup(self):
        """Add the flow input, true and false flow outputs and value component."""
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

        self.flow_in.name = "flow"
        self.flow_in.writable = True

        self.flow_out_true.name = "true"
        self.flow_out_true.readable = True
        self.flow_out_false.name = "false"
        self.flow_out_false.readable = True

        self.value_cpnt.name = "condition"
        self.value_cpnt.writable = True
        self.value_cpnt.is_editable = True
        self.value_cpnt.set_datatype(CoreDatatypes.BOOL)
        self.value_cpnt.push_value(True)

        self.components_model.add_component(self.flow_in)
        self.components_model.add_component(self.flow_out_true)
        self.components_model.add_component(self.flow_out_false)
        self.components_model.add_component(self.value_cpnt)
        self.evaluate()

    def evaluate(self):
        """Activate the flow output matching the pulled value."""
        pulled_value = bool(self.value_cpnt.pull_value())
        self.flow_out_true.is_active = pulled_value
        self.flow_out_false.is_active = not pulled_value

    def on_component_edited(self, component):
        """Evaluate again when the condition is edited or linked."""
        if component is self.value_cpnt:
            self.evaluate()
