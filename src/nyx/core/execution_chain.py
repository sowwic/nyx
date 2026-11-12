import collections
import typing
from uuid import UUID

if typing.TYPE_CHECKING:
    from .node import Node
    from nyx.stdlib.node_components.flow import FlowComponent


class ExecutionChain:
    """Finds the nodes the execution flow reaches.

    The flow of a scope begins at its flow start node and follows the flow components
    from node to node, like `StageCrawler` does. Only active flow components lead on:
    before a node is evaluated all its outputs are active, afterwards a branch or
    sequence has switched off the ones it did not choose.

    `find_flow_hops` is the one rule for where the flow goes from a node, used by the
    crawler to execute and by the editor to show the chain.
    """

    @staticmethod
    def find_flow_hops(node: Node) -> typing.Iterator[tuple[FlowComponent, Node]]:
        """Find where the flow goes from a node.

        Only flow components that are readable (not write-only data links) and active
        (not switched off by a branch or sequence) lead on, and only when linked.

        Args:
            node (Node): node the flow leaves.

        Yields:
            tuple[FlowComponent, Node]: flow component and the node its link leads to,
                wherever that node is in the stage.
        """
        if not node.is_active():
            return
        for flow_component in node.components_model.find_readable_flow_components():
            next_node = flow_component.get_next_node()
            if next_node is not None:
                yield flow_component, next_node

    @staticmethod
    def find_node_uuids(scope_node: Node) -> frozenset[UUID]:
        """Find the nodes of a scope the execution flow reaches.

        The scope itself has to be reached by the flow of its parent scope, and so on
        up to the root, otherwise nothing in it ever runs.

        Args:
            scope_node (Node): node whose children are checked.

        Returns:
            frozenset[UUID]: uuids of the children on the chain. Empty if the scope
                is not reached or has no flow start node.
        """
        if not ExecutionChain._is_scope_reached(scope_node):
            return frozenset()
        return ExecutionChain._walk_scope(scope_node)

    @staticmethod
    def _is_scope_reached(scope_node: Node) -> bool:
        """Check that the flow of every parent scope reaches the node holding it.

        Args:
            scope_node (Node): scope to check.

        Returns:
            bool: all ancestors are on the chain of their own scope.
        """
        node = scope_node
        parent = node.parent()
        while parent is not None:
            if node.uuid not in ExecutionChain._walk_scope(parent):
                return False
            node, parent = parent, parent.parent()
        return True

    @staticmethod
    def _walk_scope(scope_node: Node) -> frozenset[UUID]:
        """Follow the flow components from the flow start node of a scope.

        Args:
            scope_node (Node): scope to walk.

        Returns:
            frozenset[UUID]: uuids of the children on the flow, cycles included once.
        """
        flow_start = scope_node.find_flow_start_node()
        if flow_start is None:
            return frozenset()

        reached: set[UUID] = {flow_start.uuid}
        pending = collections.deque([flow_start])
        while pending:
            node = pending.popleft()
            for next_node in ExecutionChain._find_next_nodes(node):
                if next_node.uuid not in reached:
                    reached.add(next_node.uuid)
                    pending.append(next_node)
        return frozenset(reached)

    @staticmethod
    def _find_next_nodes(node: Node) -> typing.Iterator[Node]:
        """Find the sibling nodes the flow components of a node lead to.

        Args:
            node (Node): node the flow leaves.

        Yields:
            Node: next node, only siblings count like they do for the crawler.
        """
        parent = node.parent()
        for _flow_component, next_node in ExecutionChain.find_flow_hops(node):
            if next_node.parent() is parent:
                yield next_node
