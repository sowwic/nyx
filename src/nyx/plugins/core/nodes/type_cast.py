from nyx.api.v1 import (
    Node,
    CoreNodes,
    CoreNodeComponents,
    CoreDatatypes,
)


class TypeCastNode(Node):
    """Flow node converting an object to a type when executed."""

    DEFAULT_NAME = "type_cast"

    @classmethod
    def get_type_id(cls) -> str:
        """str: node type id."""
        return CoreNodes.TYPE_CAST

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return "Type Cast"

    @classmethod
    def get_type_icon(cls) -> str:
        """str: resource path of the type icon."""
        return ":/icons/function"

    @classmethod
    def get_description(cls) -> str:
        """str: what the node type does, shown in the palette."""
        return (
            "Converts an object to the given type when the flow reaches it, e.g. a "
            "string to an int."
        )

    @classmethod
    def get_tags(cls) -> set[str]:
        """set[str]: node tags."""
        return {"logic", "value"}

    def setup(self):
        """Add the flow, the type and object inputs and the result output."""
        self.flow_cpnt = self.components_model.create_component(CoreNodeComponents.FLOW)
        self.flow_cpnt.name = "flow"
        self.flow_cpnt.readable = True
        self.flow_cpnt.writable = True

        self.type_cpnt = self.components_model.create_component(CoreNodeComponents.VALUE)
        self.type_cpnt.name = "type"
        self.type_cpnt.default_value = "core:object"
        self.type_cpnt.writable = True
        self.type_cpnt.is_editable = True
        self.type_cpnt.set_datatype(CoreDatatypes.TYPE)

        self.object_cpnt = self.components_model.create_component(
            CoreNodeComponents.VALUE
        )
        self.object_cpnt.name = "object"
        self.object_cpnt.writable = True
        self.object_cpnt.is_editable = True
        self.object_cpnt.set_datatype(CoreDatatypes.OBJECT)

        self.result_cpnt = self.components_model.create_component(
            CoreNodeComponents.VALUE
        )
        self.result_cpnt.name = "result"
        self.result_cpnt.readable = True
        self.result_cpnt.set_datatype(CoreDatatypes.OBJECT)

        self.components_model.add_component(self.flow_cpnt)
        self.components_model.add_component(self.type_cpnt)
        self.components_model.add_component(self.object_cpnt)
        self.components_model.add_component(self.result_cpnt)

        self.bind_subtitle_to_component(
            self.type_cpnt.name,
            lambda component: getattr(
                component.pull_value(), "__name__", component.get_display_value()
            ),
        )

    def execute(self) -> None:
        """Convert the object to the type and store it as the result.

        Raises:
            TypeError: the type input isn't a class.
            ValueError: the object can't be converted to the type.
        """
        target_type = self.type_cpnt.pull_value()
        if not isinstance(target_type, type):
            raise TypeError(f"{self.path}: {target_type!r} is not a type")

        value = self.object_cpnt.pull_value()
        if not isinstance(value, target_type):
            value = target_type(value)
        # Not evaluated: a string result would be run as an expression otherwise
        self.result_cpnt.push_value(value, evaluate=False)
