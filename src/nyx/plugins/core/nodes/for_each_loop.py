from nyx.api.v1 import (
    Node,
    CoreNodes,
    CoreNodeComponents,
    CoreDatatypes,
)


class ForEachLoopNode(Node):
    """Flow node with a flow input and output, running its components when executed."""

    DEFAULT_NAME = "for_each_loop"

    @classmethod
    def get_type_id(cls) -> str:
        """str: node type id."""
        return CoreNodes.FOR_EACH_LOOP

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return "For Each Loop"

    @classmethod
    def get_type_icon(cls) -> str:
        """str: resource path of the type icon."""
        return ":/core/icons/value_cpnt"

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

        self.iterable_in_cpnt = self.components_model.create_component(
            CoreNodeComponents.VALUE
        )
        self.iterable_in_cpnt.name = "iterable"
        self.iterable_in_cpnt.writable = True
        self.iterable_in_cpnt.set_datatype(CoreDatatypes.OBJECT)

        self.reversed_toggle_in_cpnt = self.components_model.create_component(
            CoreNodeComponents.VALUE
        )
        self.reversed_toggle_in_cpnt.name = "reverse"
        self.reversed_toggle_in_cpnt.writable = True
        self.reversed_toggle_in_cpnt.set_datatype(CoreDatatypes.BOOL)
        self.reversed_toggle_in_cpnt.default_value = False

        # OUTPUTS
        self.loop_body_cpnt = self.components_model.create_component(
            CoreNodeComponents.FLOW
        )
        self.loop_body_cpnt.name = "loop_body"
        self.loop_body_cpnt.readable = True

        self.current_element_out_cpnt = self.components_model.create_component(
            CoreNodeComponents.VALUE
        )
        self.current_element_out_cpnt.name = "element"
        self.current_element_out_cpnt.readable = True
        self.current_element_out_cpnt.set_datatype(CoreDatatypes.OBJECT)

        self.current_index_cpnt = self.components_model.create_component(
            CoreNodeComponents.VALUE
        )
        self.current_index_cpnt.name = "index"
        self.current_index_cpnt.readable = True
        self.current_index_cpnt.set_datatype(CoreDatatypes.INT)

        self.flow_out_cpnt = self.components_model.create_component(
            CoreNodeComponents.FLOW
        )
        self.flow_out_cpnt.name = "completed"
        self.flow_out_cpnt.readable = True

        self.components_model.add_component(self.flow_in_cpnt)
        self.components_model.add_component(self.iterable_in_cpnt)
        self.components_model.add_component(self.reversed_toggle_in_cpnt)
        self.components_model.add_component(self.loop_body_cpnt)
        self.components_model.add_component(self.current_element_out_cpnt)
        self.components_model.add_component(self.current_index_cpnt)
        self.components_model.add_component(self.flow_out_cpnt)

    def get_self_driven_flow_components(self):
        """tuple[FlowComponent, ...]: the loop body, run by the loop itself."""
        return (self.loop_body_cpnt,)

    def execute(self) -> None:
        """Run the loop body chain for every index from first to last, inclusive."""
        iterable = self.iterable_in_cpnt.pull_value()
        try:
            iter(iterable)
        except TypeError as err:
            raise err

        crawler = self.stage.crawler
        if self.reversed_toggle_in_cpnt.pull_value():
            iterable = reversed(iterable)

        for index, element in enumerate(iterable):
            self.current_index_cpnt.push_value(index)
            self.current_element_out_cpnt.push_value(element)
            crawler.run_flow_branch(self.loop_body_cpnt)
