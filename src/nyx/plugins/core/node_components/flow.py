import pathlib
from PySide6 import QtGui

from nyx.api.v1 import (
    Node,
    NodeComponent,
    CoreNodeComponents,
    NodeComponentFlag,
    GraphicsPlugShape,
    DatatypeColor,
)


class FlowComponent(NodeComponent):
    """Static component connecting a node to the next node in the execution flow."""

    DEFAULT_NAME = "flow"
    EDITOR_QML = "FlowComponentItem"

    @classmethod
    def get_type_id(cls) -> str:
        """str: component type id."""
        return CoreNodeComponents.FLOW

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return "Flow"

    @classmethod
    def get_type_icon(cls) -> str:
        """str: resource path of the type icon."""
        return ":/core/icons/flow_cpnt"

    @classmethod
    def get_tags(cls) -> set[str]:
        """set[str]: component tags."""
        return {"logic"}

    @classmethod
    def get_default_expanded_state(cls) -> bool:
        """bool: flow components start expanded."""
        return True

    @classmethod
    def get_type_default_flags(cls) -> NodeComponentFlag:
        """NodeComponentFlag: static, readable and writable."""
        return NodeComponentFlag.STATIC

    def get_plug_color(self) -> QtGui.QColor:
        """QtGui.QColor: flow plugs are white."""
        return QtGui.QColor(DatatypeColor.FLOW)

    @classmethod
    def get_plug_shape(cls) -> GraphicsPlugShape:
        """GraphicsPlugShape: flow plugs are triangles, pointing along the flow."""
        return GraphicsPlugShape.TRIANGLE

    @classmethod
    def get_link_width_multiplier(cls) -> float:
        """float: links of the flow are drawn twice as thick as the others."""
        return 2.0

    def deserialize_value(self, value: str | None) -> pathlib.PurePosixPath | None:
        """Convert a serialized path back to a path.

        Args:
            value (str | None): serialized path.

        Returns:
            pathlib.PurePosixPath | None: path, None if no value was stored.
        """
        if value is None:
            return value
        return pathlib.PurePosixPath(value)

    def get_next_node(self) -> Node | None:
        """Get the node the flow continues with.

        Returns:
            Node | None: target node of the first output link, None if unlinked.
        """
        if self.output_links:
            return self.output_links[0].target_node
        return None
