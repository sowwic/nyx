from nyx.api.v1 import CoreNodes, CoreDatatypes, NodeComponentValueMask

from .value_collector import ValueCollectorNode


class ListNode(ValueCollectorNode):
    """Node collecting value components into a list."""

    DEFAULT_NAME = "list"
    RESULT_DATATYPE = CoreDatatypes.LIST
    RESULT_DESCRIPTION = "Result list"

    @classmethod
    def get_type_id(cls) -> str:
        """str: node type id."""
        return CoreNodes.LIST

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return "List"

    @classmethod
    def get_type_icon(cls) -> str:
        """str: resource path of the type icon."""
        return ":/core/icons/array"

    @classmethod
    def get_description(cls) -> str:
        """str: what the node type does, shown in the palette."""
        return "Collects value components and creates a list result."

    @classmethod
    def get_tags(cls) -> set[str]:
        """set[str]: node tags."""
        return {"value", "list"}

    def build_result(
        self, value_mask: NodeComponentValueMask = NodeComponentValueMask.CACHE
    ) -> list:
        """Collect the values of the value components in order.

        Args:
            value_mask (NodeComponentValueMask): which value to read from each component.

        Returns:
            list: value of each component, those of the sources first.
        """
        return [
            each_cpnt.pull_value(value_mask)
            for each_cpnt in self.collect_value_components()
        ]
