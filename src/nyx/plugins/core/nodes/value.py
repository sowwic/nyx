from nyx.api.v1 import Node, CoreNodes, CoreNodeComponents, NodeComponentFlag


class ValueNode(Node):
    """Flow node with a flow input and output, running its components when executed."""

    DEFAULT_NAME = "value"

    @classmethod
    def get_type_id(cls) -> str:
        """str: node type id."""
        return CoreNodes.VALUE

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return "Value"

    @classmethod
    def get_type_icon(cls) -> str:
        """str: resource path of the type icon."""
        return ":/core/icons/value_cpnt"

    @classmethod
    def get_description(cls) -> str:
        """str: what the node type does, shown in the palette."""
        return "Provides a value that can be edited and linked to other nodes."

    @classmethod
    def get_tags(cls) -> set[str]:
        """set[str]: node tags."""
        return {"common", "value"}

    def setup(self):
        """Add the flow component."""
        self.value_cpnt = self.components_model.create_component(
            CoreNodeComponents.VALUE
        )
        self.value_cpnt.name = "value"
        self.value_cpnt.readable = True
        self.value_cpnt.is_editable = True
        self.value_cpnt.component_flags |= NodeComponentFlag.INHERITS_DATATYPE

        self.components_model.add_component(self.value_cpnt)

        self.bind_subtitle_to_component(
            self.value_cpnt.name,
            lambda reference: reference.display_value,
        )
