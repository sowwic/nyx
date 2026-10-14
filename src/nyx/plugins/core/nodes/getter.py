from nyx.api.v1 import (
    Node,
    CoreNodes,
    CoreNodeComponents,
    NodeComponentValueMask,
    static_vars,
    exceptions,
)


class GetterNode(Node):
    DEFAULT_NAME = "get"

    @classmethod
    def get_type_id(cls) -> str:
        return CoreNodes.GET

    @classmethod
    def get_type_display_name(cls) -> str:
        return "Get"

    @classmethod
    def get_type_icon(cls) -> str:
        return ":/icons/function"

    @classmethod
    def get_tags(cls) -> set[str]:
        return {"logic", "value"}

    def get_pull_value_from_path(
        self, value_mask: NodeComponentValueMask = NodeComponentValueMask.CACHE
    ):
        node = self.stage.get_object(
            self.in_node_path.pull_value(value_mask), expected_type=Node
        )
        component = node.components_model.get_component(
            self.in_cpnt_name.pull_value(value_mask)
        )

        return component.pull_value()

    def get_pulled_display_value(self) -> str:
        try:
            node = self.stage.get_object(
                self.in_node_path.pull_value(), expected_type=Node
            )
            component = node.components_model.get_component(
                self.in_cpnt_name.pull_value()
            )
        except exceptions.StageObjectQueryError, ValueError:
            return ""

        return component.get_display_value()

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
        self.value_cpnt.is_editable = False

        self.components_model.add_component(self.in_node_path)
        self.components_model.add_component(self.in_cpnt_name)
        self.components_model.add_component(self.value_cpnt)

        # Replace pull value to pull path from inputs
        self.value_cpnt.pull_value = self.get_pull_value_from_path
        self.value_cpnt.get_display_value = self.get_pulled_display_value
