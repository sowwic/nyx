import typing
import logging
from collections.abc import Iterator

from nyx.api.v1 import (
    Node,
    CoreNodes,
    CoreNodeComponents,
    CoreDatatypes,
    NodeComponentValueMask,
    exceptions,
)

if typing.TYPE_CHECKING:
    from ..node_components.object_path import StageObjectPathComponent
    from ..node_components.value import ValueComponent


LOGGER = logging.getLogger(__name__)


class DictionaryNode(Node):
    """Node collecting value components into a dictionary."""

    DEFAULT_NAME = "dict"

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
        return ":/core/icons/branch_node"

    @classmethod
    def get_description(cls) -> str:
        """str: what the node type does, shown in the palette."""
        return "Collects value components and creates a dictionary result."

    @classmethod
    def get_tags(cls) -> set[str]:
        """set[str]: node tags."""
        return {"value"}

    def setup(self):
        """Add the result dictionary component."""
        self.result_dict_cpnt = self.components_model.create_component(
            CoreNodeComponents.VALUE
        )
        self.result_dict_cpnt.name = "result"
        self.result_dict_cpnt.description = "Result dictionary"
        self.result_dict_cpnt.readable = True
        self.result_dict_cpnt.set_datatype(CoreDatatypes.DICT)
        self.result_dict_cpnt.set_providers(
            pull=self.build_result_dict, display=self.get_result_display_value
        )

        # self.components_model.add_component(self.flow_cpnt)
        self.components_model.add_component(self.result_dict_cpnt)

    def collect_source_nodes(self) -> list[Node]:
        source_nodes = []
        object_path_components: Iterator[StageObjectPathComponent] = (
            self.components_model.find_components_of_type(
                type_id=CoreNodeComponents.STAGE_OBJECT_PATH
            )
        )
        for each_path_cpnt in object_path_components:
            try:
                source_nodes.append(each_path_cpnt.resolve_node())
            except exceptions.StageObjectQueryError:
                continue
        return source_nodes

    def collect_value_components(self) -> list[ValueComponent]:
        value_components = []

        source_nodes = self.collect_source_nodes()
        for each_node in source_nodes:
            value_components.extend(
                list(
                    each_node.components_model.find_components_of_type(
                        CoreNodeComponents.VALUE
                    )
                )
            )
        this_node_value_cpnts = list(
            self.components_model.find_components_of_type(
                type_id=CoreNodeComponents.VALUE
            )
        )
        this_node_value_cpnts.remove(self.result_dict_cpnt)
        value_components.extend(this_node_value_cpnts)

        return value_components

    def build_result_dict(
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

    def get_result_display_value(self) -> str:
        """Get the result dictionary as text, as the UI needs a string.

        Returns:
            str: dictionary text, empty if a source can't be read.
        """
        try:
            return str(self.build_result_dict())
        except Exception as err:
            LOGGER.debug("%s: can't show the result: %s", self.path, err)
            return ""
