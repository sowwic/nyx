from PySide6 import QtGui
from nyx.api.v1 import (
    Node,
    NodeComponent,
    CoreNodes,
    CoreNodeComponents,
    NodeComponentValueMask,
    NodeComponentFlag,
    exceptions,
)


class GetterNode(Node):
    """Node providing the value of a component of another node."""

    DEFAULT_NAME = "get"

    @classmethod
    def get_type_id(cls) -> str:
        """str: node type id."""
        return CoreNodes.GET

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return "Get"

    @classmethod
    def get_type_icon(cls) -> str:
        """str: resource path of the type icon."""
        return ":/icons/function"

    @classmethod
    def get_description(cls) -> str:
        """str: what the node type does, shown in the palette."""
        return "Provides the value of a component of another node."

    @classmethod
    def get_tags(cls) -> set[str]:
        """set[str]: node tags."""
        return {"logic", "value"}

    def get_pull_value_from_path(
        self, value_mask: NodeComponentValueMask = NodeComponentValueMask.CACHE
    ):
        """Pull the value of the component the node points at.

        Args:
            value_mask (NodeComponentValueMask): which value to read from the component.

        Returns:
            typing.Any: pulled value.

        Raises:
            StageObjectQueryError: if the component doesn't exist.
        """
        return self.in_component_path.resolve_component().pull_value(value_mask)

    def get_pointed_component(self) -> NodeComponent | None:
        """Get the component the node points at.

        Returns:
            NodeComponent | None: the component, None if it doesn't exist.
        """
        try:
            return self.in_component_path.resolve_component()
        except exceptions.StageObjectQueryError:
            return None

    def get_pulled_display_value(self) -> str:
        """Get the display value of the component the node points at.

        Returns:
            str: display value, empty if the component doesn't exist.
        """
        try:
            component = self.in_component_path.resolve_component()
        except exceptions.StageObjectQueryError:
            return ""

        return component.get_display_value()

    def setup(self):
        """Add the component path and value components."""
        self.in_component_path = self.components_model.create_component(
            CoreNodeComponents.STAGE_OBJECT_PATH
        )
        self.in_component_path.name = "component"
        self.in_component_path.description = (
            "Path of the component to read, like /stage/node.component."
        )
        # A node is no use here: the value of a component is needed.
        self.in_component_path.target_types = (NodeComponent,)
        self.in_component_path.is_editable = True

        self.value_cpnt = self.components_model.create_component(
            CoreNodeComponents.VALUE
        )
        self.value_cpnt.name = "value"
        self.value_cpnt.description = "Value of the component the path points at."
        self.value_cpnt.readable = True
        self.value_cpnt.component_flags |= NodeComponentFlag.INHERITS_DATATYPE
        self.value_cpnt.is_editable = False

        self.components_model.add_component(self.in_component_path)
        self.components_model.add_component(self.value_cpnt)
        self.bind_subtitle_to_component(
            self.in_component_path.name, lambda path: path.current_name_text()
        )

        # Replace pull value to pull path from inputs
        self.value_cpnt.pull_value = self.get_pull_value_from_path
        self.value_cpnt.get_display_value = self.get_pulled_display_value
        self.value_cpnt.get_plug_color = self.get_pulled_plug_color
        self.value_cpnt.get_datatype_source = self.get_pointed_component

        # The value is the one of the component the path points at: when the path
        # changes, views have to ask for it again.
        self.components_model.add_dependency(
            dependent=self.value_cpnt,
            on=self.in_component_path,
            refresh=(
                NodeComponent.Roles.CACHED_VALUE,
                NodeComponent.Roles.DISPLAY_VALUE,
                NodeComponent.Roles.IS_VALID,
                NodeComponent.Roles.RESOLVED_DATATYPE,
                NodeComponent.Roles.IS_DATATYPE_LOCKED,
            ),
        )

    def get_pulled_plug_color(self) -> QtGui.QColor:
        """Get the plug color of the component the node points at.

        Returns:
            QtGui.QColor: color of the pointed at component, the default one if the
                component doesn't exist.
        """
        try:
            return self.in_component_path.resolve_component().get_plug_color()
        except exceptions.StageObjectQueryError:
            return QtGui.QColor(NodeComponent.DEFAULT_PLUG_COLOR)
