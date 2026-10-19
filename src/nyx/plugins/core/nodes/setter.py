from nyx.api.v1 import (
    Node,
    NodeComponent,
    CoreNodes,
    CoreNodeComponents,
    NodeComponentValueMask,
    static_vars,
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
    def get_tags(cls) -> set[str]:
        """set[str]: node tags."""
        return {"logic", "value"}

    @classmethod
    def get_type_icon(cls) -> str:
        """str: resource path of the type icon."""
        return ":/icons/function"

    def setup(self):
        """Add the flow, node path, component name and value components."""
        self.flow_cpnt = self.components_model.create_component(CoreNodeComponents.FLOW)
        self.flow_cpnt.produces_output = True
        self.flow_cpnt.accepts_input = True
        self.flow_cpnt.name = "flow"

        self.node_path_cpnt = self.components_model.create_component(
            CoreNodeComponents.VALUE
        )
        self.node_path_cpnt.name = "node_path"
        self.node_path_cpnt.accepts_input = True
        self.node_path_cpnt.is_editable = True
        self.node_path_cpnt.default_value = static_vars.ROOT_NODE_PATH.as_posix()

        self.component_name_cpnt = self.components_model.create_component(
            CoreNodeComponents.VALUE
        )
        self.component_name_cpnt.name = "cpnt_name"
        self.component_name_cpnt.is_editable = True
        self.component_name_cpnt.accepts_input = True

        self.value_cpnt = self.components_model.create_component(
            CoreNodeComponents.VALUE
        )
        self.value_cpnt.name = "value"
        self.value_cpnt.is_editable = True
        self.value_cpnt.accepts_input = True

        self.components_model.add_component(self.flow_cpnt)
        self.components_model.add_component(self.node_path_cpnt)
        self.components_model.add_component(self.component_name_cpnt)
        self.components_model.add_component(self.value_cpnt)

    def execute(self):
        """Push the value into the target component."""
        node = self.stage.get_object(self.node_path_cpnt.pull_value(), Node)
        component: NodeComponent = node.components_model.get_component(
            self.component_name_cpnt.pull_value()
        )
        component.push_value(
            self.value_cpnt.pull_value(value_mask=NodeComponentValueMask.CACHE),
            evaluate=False,
        )
