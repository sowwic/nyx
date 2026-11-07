import typing
import logging
from collections.abc import Iterator

from nyx.api.v1 import (
    Node,
    CoreNodeComponents,
    NodeComponentValueMask,
    exceptions,
)

if typing.TYPE_CHECKING:
    from ..node_components.object_path import StageObjectPathComponent
    from ..node_components.value import ValueComponent


LOGGER = logging.getLogger(__name__)


class ValueCollectorNode(Node):
    """Base for nodes collecting value components into a single result component.

    The values come from the value components of the node itself and from the nodes
    its object path components point at. Subclasses choose the datatype of the result
    and how the values are put together.
    """

    RESULT_DATATYPE: str
    RESULT_DESCRIPTION: str = "Collected values"

    def setup(self):
        """Add the result component."""
        self.result_cpnt = self.components_model.create_component(
            CoreNodeComponents.VALUE
        )
        self.result_cpnt.name = "result"
        self.result_cpnt.description = self.RESULT_DESCRIPTION
        self.result_cpnt.readable = True
        self.result_cpnt.inspector_hidden = True
        self.result_cpnt.set_datatype(self.RESULT_DATATYPE)
        self.result_cpnt.set_providers(
            pull=self.build_result, display=self.get_result_display_value
        )

        self.components_model.add_component(self.result_cpnt)

    def collect_source_nodes(self) -> list[Node]:
        """Get the nodes the object path components of the node point at.

        Returns:
            list[Node]: source nodes, paths that can't be resolved are skipped.
        """
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
        """Get the value components to collect, those of the sources first.

        Returns:
            list[ValueComponent]: value components, without the result.
        """
        value_components = []

        for each_node in self.collect_source_nodes():
            value_components.extend(
                each_node.components_model.find_components_of_type(
                    CoreNodeComponents.VALUE
                )
            )
        this_node_value_cpnts = list(
            self.components_model.find_components_of_type(
                type_id=CoreNodeComponents.VALUE
            )
        )
        this_node_value_cpnts.remove(self.result_cpnt)
        value_components.extend(this_node_value_cpnts)

        return value_components

    def build_result(
        self, value_mask: NodeComponentValueMask = NodeComponentValueMask.CACHE
    ) -> typing.Any:
        """Put the values of the collected components together.

        Args:
            value_mask (NodeComponentValueMask): which value to read from each component.

        Returns:
            typing.Any: the result value.
        """
        raise NotImplementedError

    def get_result_display_value(self) -> str:
        """Get the result as text, as the UI needs a string.

        Returns:
            str: result text, empty if a source can't be read.
        """
        try:
            return str(self.build_result())
        except Exception as err:
            LOGGER.debug("%s: can't show the result: %s", self.path, err)
            return ""
