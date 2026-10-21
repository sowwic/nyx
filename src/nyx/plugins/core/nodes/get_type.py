from nyx.api.v1 import Node, CoreNodes, CoreNodeComponents, CoreDatatypes


class GetTypeNode(Node):
    """Flow node finding the type of an object when executed."""

    DEFAULT_NAME = "get_type"

    @classmethod
    def get_type_id(cls) -> str:
        """str: node type id."""
        return CoreNodes.GET_TYPE

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return "Get Type"

    @classmethod
    def get_type_icon(cls) -> str:
        """str: resource path of the type icon."""
        return ":/icons/function"

    @classmethod
    def get_description(cls) -> str:
        """str: what the node type does, shown in the palette."""
        return "Finds the type of an object when the flow reaches it."

    @classmethod
    def get_tags(cls) -> set[str]:
        """set[str]: node tags."""
        return {"logic", "value"}

    def setup(self):
        """Add the flow, the object input and the type output."""
        self.flow_cpnt = self.components_model.create_component(CoreNodeComponents.FLOW)
        self.flow_cpnt.name = "flow"
        self.flow_cpnt.readable = True
        self.flow_cpnt.writable = True

        self.object_cpnt = self.components_model.create_component(
            CoreNodeComponents.VALUE
        )
        self.object_cpnt.name = "object"
        self.object_cpnt.writable = True
        self.object_cpnt.is_editable = True
        self.object_cpnt.set_datatype(CoreDatatypes.OBJECT)

        self.type_cpnt = self.components_model.create_component(CoreNodeComponents.VALUE)
        self.type_cpnt.name = "type"
        self.type_cpnt.readable = True
        self.type_cpnt.set_datatype(CoreDatatypes.TYPE)

        self.components_model.add_component(self.flow_cpnt)
        self.components_model.add_component(self.object_cpnt)
        self.components_model.add_component(self.type_cpnt)

        self.bind_subtitle_to_component(
            self.type_cpnt.name,
            lambda component: getattr(
                component.pull_value(), "__name__", component.get_display_value()
            ),
        )

    def execute(self) -> None:
        """Store the type of the object."""
        # Not evaluated: the type is stored as it is
        self.type_cpnt.push_value(type(self.object_cpnt.pull_value()), evaluate=False)
