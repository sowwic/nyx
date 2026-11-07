from nyx.api.v1 import CoreNodes, CoreDatatypes, NodeComponentValueMask

from .value_collector import ValueCollectorNode


class DictionaryNode(ValueCollectorNode):
    """Node collecting value components into a dictionary."""

    DEFAULT_NAME = "dict"
    RESULT_DATATYPE = CoreDatatypes.DICT
    RESULT_DESCRIPTION = "Result dictionary"

    @classmethod
    def get_type_id(cls) -> str:
        """str: node type id."""
        return CoreNodes.DICT

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return "Dict"

    @classmethod
    def get_type_icon(cls) -> str:
        """str: resource path of the type icon."""
        return ":/core/icons/dictionary"

    @classmethod
    def get_description(cls) -> str:
        """str: what the node type does, shown in the palette."""
        return "Collects value components and creates a dictionary result."

    @classmethod
    def get_tags(cls) -> set[str]:
        """set[str]: node tags."""
        return {"value", "dict"}

    def build_result(
        self, value_mask: NodeComponentValueMask = NodeComponentValueMask.CACHE
    ) -> dict:
        """Collect the values of the value components by display name.

        Args:
            value_mask (NodeComponentValueMask): which value to read from each component.

        Returns:
            dict: value of each component, keyed by its display name.
        """
        return {
            each_cpnt.display_name: each_cpnt.pull_value(value_mask)
            for each_cpnt in self.collect_value_components()
        }
