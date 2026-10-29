import collections.abc
import functools
import logging
import typing
from typing import Protocol, runtime_checkable


from .contexts.execution import NodeExecutionContext
from .execution_chain import ExecutionChain
from ..static.enums import NodeExecutionOrderFlag

if typing.TYPE_CHECKING:
    from ..core import Node, Stage
    from nyx.stdlib.nodes.flow_start import FlowStartNode
    from nyx.stdlib.node_components.flow import FlowComponent

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
    - ``core:flow`` components with ``readable == False`` are write/inout
      only and are never treated as traversable paths.
    - A ``core:flow`` component can only ever point to a sibling under the
      same parent; anything else is treated as a misconfiguration and logged.
    - A node that was already reached in the run is not followed again, so
      convergence and cycles end instead of repeating.

    The walk is depth-first but iterative: the steps still to do are kept on a stack
    instead of in recursive calls, so the length of a flow chain is not limited by the
    recursion limit. Which flow components lead on is decided by ``ExecutionChain``,
    the same rule the editor uses to show the chain.
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
        self._visited_node_path_set: set[str] = set()
        self._followed_node_paths: set[str] = set()
        self._execution_paths_stack: list[str] = []
        self._current_node: Node | None = None
        self._pending_steps: list[collections.abc.Callable[[], None]] = []
        self._is_running_steps = False
        self._context = NodeExecutionContext(stage)

    @property
    def stage(self) -> Stage:
        """Stage: stage being crawled."""
        return self._stage

    @property
    def context(self) -> NodeExecutionContext:
        """NodeExecutionContext: state shared by the nodes of the current crawl."""
        return self._context

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
        self._visited_node_path_set.clear()
        self._followed_node_paths.clear()
        self.execution_paths_stack.clear()

    def start(self, start_node: Node | None = None) -> None:
        """Begin (or restart) a crawl from ``start_node`` or the stage root."""
        self.clear_cached_data()
        self._context = NodeExecutionContext(self.stage)
        self.stage.execution_started.emit()
        start_node: Node | FlowStartNode | None = start_node or self.stage.root_node
        try:
            self._traverse_children(start_node)  # kicks off the descent
        finally:
            # A failing node leaves scopes open, their cleanups still have to run.
            self._context.unwind()
        self.stage.execution_succeeded.emit()
        self.stage.execution_finished.emit()

    def run_flow_branch(self, flow_component: FlowComponent) -> None:
        """Run the chain a flow component leads to, now, before returning.

        Meant for nodes that run a chain more than once, like a loop. The nodes of
        the chain count as not visited again afterwards, so the same chain can be
        run again.

        Args:
            flow_component (FlowComponent): flow component whose chain to run.
        """
        next_node = flow_component.get_next_node()
        if next_node is None:
            return
        if next_node.parent() != flow_component.node.parent():
            raise RuntimeError(
                f"{flow_component.path} points to "
                f"{next_node.path}, which is not a sibling node.",
            )

        visited_paths = list(self._visited_node_paths)
        visited_path_set = set(self._visited_node_path_set)
        followed_paths = set(self._followed_node_paths)
        pending_steps = self._pending_steps
        was_running_steps = self._is_running_steps
        self._pending_steps = []
        self._is_running_steps = False
        try:
            self._traverse_children(next_node)
        finally:
            self._pending_steps = pending_steps
            self._is_running_steps = was_running_steps
            self._visited_node_paths[:] = visited_paths
            self._visited_node_path_set.clear()
            self._visited_node_path_set.update(visited_path_set)
            self._followed_node_paths.clear()
            self._followed_node_paths.update(followed_paths)

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
        self._visited_node_path_set.add(node_path_as_string)

        node_execution_order = node.get_type_execution_order()

        # The scope of a node lasts while its children execute. It is closed by a
        # step scheduled before them, which runs once all of them are done.
        if node_execution_order is NodeExecutionOrderFlag.BEFORE_CHILDREN:
            self._schedule(
                functools.partial(self._execute_node_and_record_its_path, node),
                functools.partial(self._open_scope_of_node, node),
                functools.partial(self._resolve_children_of_node, node),
                self._context_pop_scope,
            )
        elif node_execution_order is NodeExecutionOrderFlag.AFTER_CHILDREN:
            self._schedule(
                functools.partial(self._open_scope_of_node, node),
                functools.partial(self._resolve_children_of_node, node),
                self._context_pop_scope,
                functools.partial(self._execute_node_and_record_its_path, node),
            )
        self._run_scheduled_steps()

    def _has_node_already_been_visited(self, node_path_as_string: str) -> bool:
        """Check whether a node path was already visited.

        Args:
            node_path_as_string (str): node path.

        Returns:
            bool: node was visited.
        """
        return node_path_as_string in self._visited_node_path_set

    def _execute_node_and_record_its_path(self, node: Node) -> None:
        """Run the node's execution hook and record its path.

        Args:
            node (Node): node to execute.
        """
        self._current_node = node
        LOGGER.debug("Executing node %s", node.path)
        node.execution_hook()
        self._execution_paths_stack.append(node.path.as_posix())

    def _open_scope_of_node(self, node: Node) -> None:
        """Open the execution scope of a node and let the node fill it.

        Args:
            node (Node): node whose children are about to execute.
        """
        self._context.push_scope(node)
        node.enter_scope(self._context)

    def _context_pop_scope(self) -> None:
        """Close the innermost execution scope."""
        self._context.pop_scope()

    def _resolve_children_of_node(self, node: Node) -> None:
        """Schedule the traversal of the node's children from its flow start node.

        Args:
            node (Node): parent node.
        """
        # Fully resolve this node's own children before anything else.
        flow_start_child_node = node.find_flow_start_node()
        if flow_start_child_node is not None:
            self._schedule(
                functools.partial(self._traverse_children, flow_start_child_node)
            )

    def _traverse_children(self, child_node: Node) -> None:
        """Visit a child node, then the flow siblings that follow it.

        Args:
            child_node (Node): node to start from.
        """
        node_path_as_string = str(child_node.path)
        if node_path_as_string in self._followed_node_paths:
            LOGGER.warning(
                "Cycle/convergence at %s, not following it again", node_path_as_string
            )
            return
        self._followed_node_paths.add(node_path_as_string)

        # Steps are taken off a stack, so what is scheduled last runs first. The
        # siblings are scheduled before the visit and so run after all of it: the
        # child's own children and the child itself. Only then do we look at its
        # core:flow components, which a branch sets while executing.
        self._schedule(functools.partial(self._traverse_next_nodes, child_node))
        child_node.accept_visitor(self)
        self._run_scheduled_steps()

    def _traverse_next_nodes(self, node: Node) -> None:
        """Schedule the traversal of the flow siblings that follow a node.

        Args:
            node (Node): node that was just visited.
        """
        next_nodes = self._find_next_nodes(node)
        self._schedule(
            *(
                functools.partial(self._traverse_children, next_node)
                for next_node in next_nodes
            )
        )

    def _find_next_nodes(self, node: Node) -> list[Node]:
        """Resolve the (possibly zero, one, or many) next nodes after ``node``.

        Only considers ``core:flow`` components that are both active (the
        branch/sequence chose this path) and readable (not inout/write-only
        data links). Resolution is restricted to siblings of ``node`` under
        the same parent -- a flow component is not expected to point anywhere
        else.

        Raises:
            RuntimeError: if a flow component points at a node that is not a sibling.
        """
        next_nodes: list[Node] = []
        self_driven = node.get_self_driven_flow_components()
        for flow_component, next_node in ExecutionChain.find_flow_hops(node):
            if flow_component in self_driven:
                continue
            if next_node.parent() != node.parent():
                raise RuntimeError(
                    f"{flow_component.path} points to "
                    f"{next_node.path}, which is not a sibling node.",
                )
            next_nodes.append(next_node)

        return next_nodes

    # -- Steps -----------------------------------------------------------

    def _schedule(self, *steps: collections.abc.Callable[[], None]) -> None:
        """Schedule steps to run in the given order, before anything scheduled earlier.

        Args:
            *steps (Callable[[], None]): steps, the first one runs first.
        """
        self._pending_steps.extend(reversed(steps))

    def _run_scheduled_steps(self) -> None:
        """Run the scheduled steps until none is left.

        Steps scheduled while running are run too. Called while already running, it
        does nothing: the loop that is running picks up the new steps.
        """
        if self._is_running_steps:
            return

        self._is_running_steps = True
        try:
            while self._pending_steps:
                self._pending_steps.pop()()
        finally:
            self._pending_steps.clear()
            self._is_running_steps = False
