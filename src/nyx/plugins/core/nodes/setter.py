from nyx.api.v1 import Node, NodeComponent, CoreNodes, CoreNodeComponents, static_vars


class SetterNode(Node):
    DEFAULT_NAME = "set"
    REQUIRED_PLUGINS = {"NyxCore"}

    @classmethod
    def get_type_id(cls) -> str:
        return CoreNodes.SET

    @classmethod
    def get_type_display_name(cls) -> str:
        return "Set"

    @classmethod
    def get_tags(cls) -> set[str]:
        return {"logic", "value"}

    def setup(self):
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
        node = self.stage.get_object(self.node_path_cpnt.pull_value(), Node)
        component: NodeComponent = node.components_model.get_component(
            self.component_name_cpnt.pull_value()
        )
        component.value = self.value_cpnt.value
