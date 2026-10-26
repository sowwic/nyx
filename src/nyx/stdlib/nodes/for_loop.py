from nyx.api.v1 import (
    Node,
    CoreNodes,
    CoreNodeComponents,
    CoreDatatypes,
)


class ForLoopNode(Node):
    """Flow node with a flow input and output, running its components when executed."""

    DEFAULT_NAME = "for_loop"

    @classmethod
    def get_type_id(cls) -> str:
        """str: node type id."""
        return CoreNodes.FOR_LOOP

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return "For Loop"

    @classmethod
    def get_type_icon(cls) -> str:
        """str: resource path of the type icon."""
        return ":/core/icons/value_cpnt"

    @classmethod
    def get_description(cls) -> str:
        """str: what the node type does, shown in the palette."""
        return (
            "Runs the loop body for every index from the first to the last index, "
            "then continues with completed."
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
        self.flow_in_cpnt.description = "Execution flow into the node."
        self.flow_in_cpnt.writable = True

        self.first_index_cpnt = self.components_model.create_component(
            CoreNodeComponents.VALUE
        )
        self.first_index_cpnt.name = "first_index"
        self.first_index_cpnt.description = "Index the loop starts with."
        self.first_index_cpnt.writable = True
        self.first_index_cpnt.is_editable = True
        self.first_index_cpnt.set_datatype(CoreDatatypes.INT)

        self.last_index_cpnt = self.components_model.create_component(
            CoreNodeComponents.VALUE
        )
        self.last_index_cpnt.name = "last_index"
        self.last_index_cpnt.description = "Index the loop ends with, this one included."
        self.last_index_cpnt.writable = True
        self.last_index_cpnt.is_editable = True
        self.last_index_cpnt.set_datatype(CoreDatatypes.INT)

        # OUTPUTS
        self.loop_body_cpnt = self.components_model.create_component(
            CoreNodeComponents.FLOW
        )
        self.loop_body_cpnt.name = "loop_body"
        self.loop_body_cpnt.description = "Flow that runs once for every index."
        self.loop_body_cpnt.readable = True

        self.current_index_cpnt = self.components_model.create_component(
            CoreNodeComponents.VALUE
        )
        self.current_index_cpnt.name = "index"
        self.current_index_cpnt.description = (
            "Index of the current run of the loop body."
        )
        self.current_index_cpnt.readable = True
        self.current_index_cpnt.set_datatype(CoreDatatypes.INT)

        self.flow_out_cpnt = self.components_model.create_component(
            CoreNodeComponents.FLOW
        )
        self.flow_out_cpnt.name = "completed"
        self.flow_out_cpnt.description = (
            "Flow that continues after the last run of the loop body."
        )
        self.flow_out_cpnt.readable = True

        self.components_model.add_component(self.flow_in_cpnt)
        self.components_model.add_component(self.first_index_cpnt)
        self.components_model.add_component(self.last_index_cpnt)
        self.components_model.add_component(self.loop_body_cpnt)
        self.components_model.add_component(self.current_index_cpnt)
        self.components_model.add_component(self.flow_out_cpnt)

    def get_self_driven_flow_components(self):
        """tuple[FlowComponent, ...]: the loop body, run by the loop itself."""
        return (self.loop_body_cpnt,)

    def execute(self) -> None:
        """Run the loop body chain for every index from first to last, inclusive."""
        first_index = int(self.first_index_cpnt.pull_value())
        last_index = int(self.last_index_cpnt.pull_value())
        crawler = self.stage.crawler

        for index in range(first_index, last_index + 1):
            self.current_index_cpnt.push_value(index)
            crawler.run_flow_branch(self.loop_body_cpnt)
