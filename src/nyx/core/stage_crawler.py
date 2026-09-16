import logging
import typing
from typing import Protocol, runtime_checkable

if typing.TYPE_CHECKING:
    from nyx.core import Node, Stage

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
    - ``core:flow`` components with ``is_readable == False`` are write/inout
      only and are never treated as traversable paths.
    - A ``core:flow`` component can only ever point to a sibling under the
      same parent; anything else is treated as a misconfiguration and logged.
    """

    def __repr__(self) -> str:
        return f"StageCrawler({self.stage!r})"

    def __init__(self, stage: Stage) -> None:
        self._stage = stage
        self._visited_node_paths: list[str] = []
        self._current_node: Node | None = None

    @property
    def stage(self) -> Stage:
        return self._stage

    @property
    def current_node(self) -> Node | None:
        return self._current_node

    @property
    def visited_node_paths(self) -> list[str]:
        return self._visited_node_paths

    def start(self, start_node: Node | None = None) -> None:
        """Begin (or restart) a crawl from ``start_node`` or the stage root."""
        self._visited_node_paths.clear()
        root = start_node or self.stage.root_node.find_flow_start_node()
        if root is None:
            raise RuntimeError(
                f"No start node given and {self.stage!r} has no root_node"
            )
        root.accept_visitor(self)  # kicks off recursive post-order descent

    # -- NodeVisitor -----------------------------------------------------

    def visit_node(self, node: Node) -> None:
        path = str(node.path)
        if path in self._visited_node_paths:
            LOGGER.warning("Cycle/convergence at %s, not re-visiting", path)
            return
        self._visited_node_paths.append(path)

        # Phase 1: fully resolve this node's own children before anything else.
        start_child = node.find_flow_start_node()
        if start_child is not None:
            self._traverse_children(start_child)

        # Phase 2: only now, after all children are done, execute this node.
        self._current_node = node
        LOGGER.debug("Executing node %s", path)
        node.execute()

    # -- internals ---------------------------------------------------------

    def _traverse_children(self, child: Node) -> None:
        # child.accept(self) -> visit_node(child): this resolves child's own
        # children first, then executes child. Only after child has executed
        # do we look at its core:flow components to find the next flow-sibling.
        child.accept_visitor(self)

        for next_child in self._find_next_nodes(child):
            self._traverse_children(next_child)

    def _find_next_nodes(self, node: Node) -> list[Node]:
        """Resolve the (possibly zero, one, or many) next nodes after ``node``.

        Only considers ``core:flow`` components that are both active (the
        branch/sequence chose this path) and readable (not inout/write-only
        data links). Resolution is restricted to siblings of ``node`` under
        the same parent -- a flow component is not expected to point anywhere
        else.
        """
        flow_components = node.components_model.find_components_of_type("core:flow")
        eligible = [c for c in flow_components if c.is_active and c.is_readable]

        if not eligible:
            return []

        parent: Node | None = node.parent()
        if parent is None:
            LOGGER.warning(
                "Node %s has active core:flow components but no parent to resolve siblings against",
                node.path,
            )
            return []

        siblings_by_path = {
            str(sibling.path): sibling for sibling in parent.list_children()
        }

        next_nodes: list[Node] = []
        for component in eligible:
            next_node = siblings_by_path.get(component.value)
            if next_node is None:
                LOGGER.warning(
                    "core:flow on %s points to %s, which is not a sibling under %s",
                    node.path,
                    component.value,
                    parent.path,
                )
                continue
            next_nodes.append(next_node)

        return next_nodes
