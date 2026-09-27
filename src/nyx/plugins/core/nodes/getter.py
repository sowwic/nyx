from nyx.api.v1 import Node, CoreNodes, CoreNodeComponents, static_vars


class GetterNode(Node):
    DEFAULT_NAME = "get"
    REQUIRED_PLUGINS = {"NyxCore"}

    @classmethod
    def get_type_id(cls) -> str:
        return CoreNodes.GET

    @classmethod
    def get_type_display_name(cls) -> str:
        return "Get"

    @classmethod
    def get_tags(cls) -> set[str]:
        return {"logic", "value"}

    def get_pull_value_from_path(self):
        node = self.stage.get_object(self.in_node_path.value, expected_type=Node)
        component = node.components_model.get_component(self.in_cpnt_name.value)

        return component.value

    def setup(self):
        self.in_node_path = self.components_model.create_component(
            CoreNodeComponents.VALUE
        )
        self.in_node_path.name = "node_path"
        self.in_node_path.is_editable = True
        self.in_node_path.default_value = static_vars.ROOT_NODE_PATH.as_posix()

        self.in_cpnt_name = self.components_model.create_component(
            CoreNodeComponents.VALUE
        )
        self.in_cpnt_name.name = "cpnt_name"
        self.in_cpnt_name.is_editable = True

        self.value_cpnt = self.components_model.create_component(
            CoreNodeComponents.VALUE
        )
        self.value_cpnt.name = "value"
        self.value_cpnt.produces_output = True

        self.components_model.add_component(self.in_node_path)
        self.components_model.add_component(self.in_cpnt_name)
        self.components_model.add_component(self.value_cpnt)

        # Replace pull value to pull path from inputs
        self.value_cpnt.pull_value = self.get_pull_value_from_path
