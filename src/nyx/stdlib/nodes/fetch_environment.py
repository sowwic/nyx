import os

from nyx.api.v1 import (
    CoreDatatypes,
    CoreNodeComponents,
    CoreNodes,
    Node,
)


class FetchEnvironmentNode(Node):
    """Flow node storing the environment variables of the application when executed."""

    DEFAULT_NAME = "fetch_environment"

    @classmethod
    def get_type_id(cls) -> str:
        """str: node type id."""
        return CoreNodes.FETCH_ENVIRONMENT

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return "Fetch Environment"

    @classmethod
    def get_type_icon(cls) -> str:
        """str: resource path of the type icon."""
        return ":/icons/settings"

    @classmethod
    def get_description(cls) -> str:
        """str: what the node type does, shown in the palette."""
        return (
            "Reads the environment variables of the application into a dictionary "
            "when the flow reaches it."
        )

    @classmethod
    def get_tags(cls) -> set[str]:
        """set[str]: node tags."""
        return {"value", "dict", "system"}

    def setup(self):
        """Add the flow input and output and the environment output."""
        self.flow_in = self.components_model.create_component(CoreNodeComponents.FLOW)
        self.flow_in.name = "flow"
        self.flow_in.description = "Execution flow into the node."
        self.flow_in.writable = True

        self.flow_out = self.components_model.create_component(CoreNodeComponents.FLOW)
        self.flow_out.name = "next"
        self.flow_out.description = "Flow that continues once the environment is read."
        self.flow_out.readable = True

        self.environment_cpnt = self.components_model.create_component(
            CoreNodeComponents.VALUE
        )
        self.environment_cpnt.name = "environment"
        self.environment_cpnt.description = (
            "Environment variables, name to value, as they were when the node ran."
        )
        self.environment_cpnt.readable = True
        self.environment_cpnt.is_editable = False
        self.environment_cpnt.set_datatype(CoreDatatypes.DICT)

        self.components_model.add_component(self.flow_in)
        self.components_model.add_component(self.flow_out)
        self.components_model.add_component(self.environment_cpnt)

        self.bind_subtitle_to_component(
            self.environment_cpnt.name,
            lambda component: f"{len(component.pull_value() or {})} variables",
        )

    def execute(self) -> None:
        """Store a copy of the environment."""
        # Not evaluated: the dictionary is stored as it is
        self.environment_cpnt.push_value(dict(os.environ), evaluate=False)
