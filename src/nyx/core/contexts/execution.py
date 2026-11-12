import contextlib
import dataclasses
import logging
import typing

if typing.TYPE_CHECKING:
    from ..node import Node
    from ..stage import Stage

LOGGER = logging.getLogger(__name__)


@dataclasses.dataclass
class ExecutionScope:
    """What a node provides to the nodes inside it while they execute.

    Attributes:
        node: node owning the scope, None for the root scope of a crawl
        services: objects provided by the scope
        cleanups: callbacks run when the scope ends
    """

    node: Node | None = None
    services: list[typing.Any] = dataclasses.field(default_factory=list)
    cleanups: contextlib.ExitStack = dataclasses.field(
        default_factory=contextlib.ExitStack
    )


class NodeExecutionContext:
    """State shared by the nodes of one crawl.

    Created by `StageCrawler.start`. The crawler opens a scope for every node while
    its children execute, so a node can `provide` something (a connection, a
    namespace) that its children `find`, and have it cleaned up when the scope ends
    even if a child fails.
    """

    def __init__(self, stage: Stage) -> None:
        """Initialize NodeExecutionContext.

        Args:
            stage (Stage): stage being crawled.
        """
        self._stage = stage
        self._scopes: list[ExecutionScope] = [ExecutionScope()]

    @property
    def stage(self) -> Stage:
        """Stage: stage being crawled."""
        return self._stage

    @property
    def current_scope(self) -> ExecutionScope:
        """ExecutionScope: innermost open scope."""
        return self._scopes[-1]

    @property
    def scope_depth(self) -> int:
        """int: number of open scopes, not counting the root one."""
        return len(self._scopes) - 1

    def push_scope(self, node: Node) -> ExecutionScope:
        """Open the scope of a node.

        Args:
            node (Node): node whose children are about to execute.

        Returns:
            ExecutionScope: new scope.
        """
        scope = ExecutionScope(node=node)
        self._scopes.append(scope)
        return scope

    def pop_scope(self) -> None:
        """Close the innermost scope and run its cleanups, most recent first.

        A failing cleanup is logged, it must not keep the other ones from running.
        """
        if len(self._scopes) == 1:
            raise RuntimeError("There is no scope to pop")
        self._close_scope(self._scopes.pop())

    def unwind(self) -> None:
        """Close every scope, the root one included, and start over with a new root.

        Used when a crawl ends, however it ends.
        """
        while self._scopes:
            self._close_scope(self._scopes.pop())
        self._scopes.append(ExecutionScope())

    def provide(self, service: typing.Any) -> None:
        """Make an object available to the nodes in the current scope.

        Args:
            service (Any): object to provide.
        """
        self.current_scope.services.append(service)

    def add_cleanup(self, callback: typing.Callable[[], typing.Any]) -> None:
        """Run a callback when the current scope ends.

        Args:
            callback (Callable[[], Any]): callback.
        """
        self.current_scope.cleanups.callback(callback)

    def find(self, service_type: type) -> typing.Any | None:
        """Find a provided object, looking from the innermost scope outwards.

        Args:
            service_type (type): type of the object.

        Returns:
            Any | None: most recently provided instance of the type, None if there
                is none.
        """
        for scope in reversed(self._scopes):
            for service in reversed(scope.services):
                if isinstance(service, service_type):
                    return service
        return None

    def require(self, service_type: type) -> typing.Any:
        """Find a provided object that has to exist.

        Args:
            service_type (type): type of the object.

        Raises:
            LookupError: nothing of that type is provided in the open scopes.

        Returns:
            Any: most recently provided instance of the type.
        """
        service = self.find(service_type)
        if service is None:
            raise LookupError(
                f"No {service_type.__name__} provided, is the node inside "
                "a node that provides it?"
            )
        return service

    @staticmethod
    def _close_scope(scope: ExecutionScope) -> None:
        """Run the cleanups of a scope.

        Args:
            scope (ExecutionScope): scope that ended.
        """
        try:
            scope.cleanups.close()
        except Exception:
            LOGGER.exception("Scope cleanup failed for %s", scope.node)
