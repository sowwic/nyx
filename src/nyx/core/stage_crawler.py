import logging
import typing
from typing import Protocol, runtime_checkable


from ..static.enums import NodeExecutionOrderFlag

if typing.TYPE_CHECKING:
    from ..core import Node, Stage
    from nyx.plugins.core.nodes.flow_start import FlowStartNode

LOGGER = logging.getLogger(__name__)


@runtime_checkable
class NodeVisitor(Protocol):
    """Visitor interface, structural rather than nominal.

    ``Node.accept(visitor)`` should call ``visitor.visit_node(self)``. Any
    class with a matching ``visit_node`` method satisfies this Protocol --
    no inheritance required. This is the double-dispatch hook that lets new
    operations (crawling, validation, rendering, ...) be added over the Node
    hierarchy without modifying Node itself.

    ``runtime_checkable`` only lets ``isinstance(x, NodeVisitor)`` check for
    the *presence* of ``visit_node`` (not its signature) -- useful for an
    assertion or guard clause, not for full type safety. Static type
    checkers (mypy/pyright) do verify the full signature.
    """

    def visit_node(self, node: Node) -> None:
        """Fully process a node: its children's subtrees first, then the node itself."""
        ...


class StageCrawler:
    """Post-order crawler over a Stage's node graph.

    Implements the ``NodeVisitor`` protocol structurally (via ``visit_node``)
    without inheriting from it.

    Traversal rules:
    - A node's children are found via ``find_flow_start_node()`` and then
      followed via each node's ``core:flow`` components.
    - A node's *own* children (and their full subtrees) are executed before
      the node itself executes (post-order / bottom-up).
    - Branch nodes: only some of their outgoing ``core:flow`` components are
      ``is_active`` after execution -- resolved only *after* ``execute()``
      runs, never guessed ahead of time.
    - Sequence nodes: multiple outgoing ``core:flow`` components can be
      ``is_active`` simultaneously -- each is traversed fully, depth-first,
      one after another.
    - ``core:flow`` components with ``produces_output == False`` are write/inout
      only and are never treated as traversable paths.
    - A ``core:flow`` component can only ever point to a sibling under the
      same parent; anything else is treated as a misconfiguration and logged.
    """

    def __repr__(self) -> str:
        """str: crawler with its stage."""
        return f"StageCrawler({self.stage!r})"

    def __init__(self, stage: Stage) -> None:
        """Initialize StageCrawler.

        Args:
            stage (Stage): stage to crawl.
        """
        self._stage = stage
        self._visited_node_paths: list[str] = []
        self._execution_paths_stack: list[str] = []
        self._current_node: Node | None = None

    @property
    def stage(self) -> Stage:
        """Stage: stage being crawled."""
        return self._stage

    @property
    def current_node(self) -> Node | None:
        """Node | None: node currently being executed."""
        return self._current_node

    @property
    def visited_node_paths(self) -> list[str]:
        """list[str]: paths of nodes visited in the current run."""
        return self._visited_node_paths

    @property
    def execution_paths_stack(self) -> list[str]:
        """list[str]: paths of executed nodes, in execution order."""
        return self._execution_paths_stack

    def clear_cached_data(self):
        """Forget visited and executed nodes."""
        self.visited_node_paths.clear()
        self.execution_paths_stack.clear()

    def start(self, start_node: Node | None = None) -> None:
        """Begin (or restart) a crawl from ``start_node`` or the stage root."""
        self.clear_cached_data()

        start_node: Node | FlowStartNode | None = start_node or self.stage.root_node
        self._traverse_children(start_node)  # kicks off recursive post-order descent

    # -- NodeVisitor -----------------------------------------------------

    def visit_node(self, node: Node) -> None:
        """Visit a node, executing it and its children in the type's order.

        Nodes already visited in this run are skipped.

        Args:
            node (Node): node to visit.
        """
        node_path_as_string = str(node.path)

        if self._has_node_already_been_visited(node_path_as_string):
            LOGGER.warning(
                "Cycle/convergence at %s, not re-visiting", node_path_as_string
            )
            return
        self._visited_node_paths.append(node_path_as_string)

        node_execution_order = node.get_type_execution_order()

        if node_execution_order is NodeExecutionOrderFlag.BEFORE_CHILDREN:
            self._execute_node_and_record_its_path(node)
            self._resolve_children_of_node(node)
        elif node_execution_order is NodeExecutionOrderFlag.AFTER_CHILDREN:
            self._resolve_children_of_node(node)
            self._execute_node_and_record_its_path(node)

    def _has_node_already_been_visited(self, node_path_as_string: str) -> bool:
        """Check whether a node path was already visited.

        Args:
            node_path_as_string (str): node path.

        Returns:
            bool: node was visited.
        """
        return node_path_as_string in self._visited_node_paths

    def _execute_node_and_record_its_path(self, node: Node) -> None:
        """Run the node's execution hook and record its path.

        Args:
            node (Node): node to execute.
        """
        self._current_node = node
        LOGGER.debug("Executing node %s", node.path)
        node.execution_hook()
        self._execution_paths_stack.append(node.path.as_posix())

    def _resolve_children_of_node(self, node: Node) -> None:
        """Traverse the node's children starting from its flow start node.

        Args:
            node (Node): parent node.
        """
        # Fully resolve this node's own children before anything else.
        flow_start_child_node = node.find_flow_start_node()
        if flow_start_child_node is not None:
            self._traverse_children(flow_start_child_node)

    def _traverse_children(self, child_node: Node) -> None:
        """Visit a child node, then the flow siblings that follow it.

        Args:
            child_node (Node): node to start from.
        """
        # child_node.accept_visitor(self) -> visit_node(child_node): this resolves
        # the child's own children first, then executes the child. Only after the
        # child has executed do we look at its core:flow components to find the
        # next flow-sibling.
        child_node.accept_visitor(self)

        for next_sibling_node in self._find_next_nodes(child_node):
            self._traverse_children(next_sibling_node)

    def _find_next_nodes(self, node: Node) -> list[Node]:
        """Resolve the (possibly zero, one, or many) next nodes after ``node``.

        Only considers ``core:flow`` components that are both active (the
        branch/sequence chose this path) and readable (not inout/write-only
        data links). Resolution is restricted to siblings of ``node`` under
        the same parent -- a flow component is not expected to point anywhere
        else.
        """
        readable_flow_components = node.components_model.find_readable_flow_components()
        if not readable_flow_components:
            return []

        next_nodes: list[Node] = []
        for flow_component in readable_flow_components:
            next_node = flow_component.get_next_node()
            if next_node is None:
                continue

            if next_node.parent() != node.parent():
                raise RuntimeError(
                    f"{flow_component.path} points to "
                    f"{next_node.path}, which is not a sibling node.",
                )
            next_nodes.append(next_node)

        return next_nodes
