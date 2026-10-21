from nyx.api.v1 import (
    Node,
    CoreNodes,
    CoreNodeComponents,
    CoreDatatypes,
)


class WhileLoopNode(Node):
    """Flow node with a flow input and output, running its components when executed."""

    DEFAULT_NAME = "while_loop"

    @classmethod
    def get_type_id(cls) -> str:
        """str: node type id."""
        return CoreNodes.WHILE_LOOP

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return "While Loop"

    @classmethod
    def get_type_icon(cls) -> str:
        """str: resource path of the type icon."""
        return ":/core/icons/value_cpnt"

    @classmethod
    def get_description(cls) -> str:
        """str: what the node type does, shown in the palette."""
        return (
            "Runs the loop body for as long as the condition is true, then "
            "continues with completed."
        )

    @classmethod
    def get_tags(cls) -> set[str]:
        """set[str]: node tags."""
        return {"common", "logic", "cycle"}

    def setup(self):
        """Add the flow component."""
        # INPUTS
        self.flow_in_cpnt = self.components_model.create_component(
            CoreNodeComponents.FLOW
        )
        self.flow_in_cpnt.name = "flow"
        self.flow_in_cpnt.writable = True

        self.condition_in_cpnt = self.components_model.create_component(
            CoreNodeComponents.VALUE
        )
        self.condition_in_cpnt.name = "condition"
        self.condition_in_cpnt.writable = True
        self.condition_in_cpnt.set_datatype(CoreDatatypes.BOOL)

        # OUTPUTS
        self.loop_body_cpnt = self.components_model.create_component(
            CoreNodeComponents.FLOW
        )
        self.loop_body_cpnt.name = "loop_body"
        self.loop_body_cpnt.readable = True

        self.flow_out_cpnt = self.components_model.create_component(
            CoreNodeComponents.FLOW
        )
        self.flow_out_cpnt.name = "completed"
        self.flow_out_cpnt.readable = True

        self.components_model.add_component(self.flow_in_cpnt)
        self.components_model.add_component(self.condition_in_cpnt)
        self.components_model.add_component(self.loop_body_cpnt)
        self.components_model.add_component(self.flow_out_cpnt)

    def get_self_driven_flow_components(self):
        """tuple[FlowComponent, ...]: the loop body, run by the loop itself."""
        return (self.loop_body_cpnt,)

    def execute(self) -> None:
        """Run the loop body chain for every index from first to last, inclusive."""
        condition = self.condition_in_cpnt.pull_value()
        crawler = self.stage.crawler

        while condition:
            crawler.run_flow_branch(self.loop_body_cpnt)
            condition = self.condition_in_cpnt.pull_value()
