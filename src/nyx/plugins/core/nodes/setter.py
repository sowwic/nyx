from nyx.api.v1 import (
    Node,
    NodeComponent,
    CoreNodes,
    CoreNodeComponents,
    NodeComponentValueMask,
    NodeComponentFlag,
)


class SetterNode(Node):
    """Flow node setting the value of a component of another node."""

    DEFAULT_NAME = "set"

    @classmethod
    def get_type_id(cls) -> str:
        """str: node type id."""
        return CoreNodes.SET

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return "Set"

    @classmethod
    def get_description(cls) -> str:
        """str: what the node type does, shown in the palette."""
        return "Sets the value of a component of another node when the flow reaches it."

    @classmethod
    def get_tags(cls) -> set[str]:
        """set[str]: node tags."""
        return {"logic", "value"}

    @classmethod
    def get_type_icon(cls) -> str:
        """str: resource path of the type icon."""
        return ":/icons/function"

    def setup(self):
        """Add the flow, component path and value components."""
        self.flow_cpnt = self.components_model.create_component(CoreNodeComponents.FLOW)
        self.flow_cpnt.readable = True
        self.flow_cpnt.writable = True
        self.flow_cpnt.name = "flow"

        self.component_path_cpnt = self.components_model.create_component(
            CoreNodeComponents.STAGE_REFERENCE
        )
        self.component_path_cpnt.name = "component"
        self.component_path_cpnt.description = (
            "Path of the component to change, like /stage/node.component."
        )
        # A node is no use here: the value of a component is needed.
        self.component_path_cpnt.target_types = (NodeComponent,)
        self.component_path_cpnt.writable = True
        self.component_path_cpnt.is_editable = True

        self.value_cpnt = self.components_model.create_component(
            CoreNodeComponents.VALUE
        )
        self.value_cpnt.name = "value"
        self.value_cpnt.description = "Value to set."
        self.value_cpnt.component_flags |= NodeComponentFlag.INHERITS_DATATYPE
        self.value_cpnt.is_editable = True
        self.value_cpnt.writable = True

        self.components_model.add_component(self.flow_cpnt)
        self.components_model.add_component(self.component_path_cpnt)
        self.components_model.add_component(self.value_cpnt)
        self.bind_subtitle_to_component(
            self.component_path_cpnt.name,
            lambda reference: reference.current_name_text(),
        )

    def execute(self):
        """Push the value, cast to the datatype of the target, into the target.

        Raises:
            DatatypeCastError: the value can't be cast, the target is left as it is.
        """
        component: NodeComponent = self.component_path_cpnt.resolve_component()
        value = self.value_cpnt.pull_value(value_mask=NodeComponentValueMask.CACHE)
        component.push_value(component.cast_value(value), evaluate=False)
