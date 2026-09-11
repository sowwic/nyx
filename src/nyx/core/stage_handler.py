import logging
import pathlib
import timeit
import typing
from collections import deque

if typing.TYPE_CHECKING:
    from nyx.core import Node, Stage


LOGGER = logging.getLogger(__name__)


class StageHandler:
    def __repr__(self) -> str:
        return f"StageHandler ({self.stage})"

    def __init__(self, stage: Stage) -> None:
        self._stage = stage

    @property
    def stage(self):
        return self._stage

    def build_execution_queue(
        self, start_path: Node | str | pathlib.PurePosixPath | None = None
    ) -> deque[pathlib.PurePosixPath]:
        """Build execution queue from given path.

        Args:
            start_path: queue start path.

        Returns:
            Resulting queue

        """
        # TODO: Use from graphlib import TopologicalSorter to get list from tree.
        start_node = self.stage.node(start_path)
        if not start_node:
            start_path = self.stage.get_execution_start_path(start_path)
        if start_path is None:
            LOGGER.warning(
                f"{self} | No execution start path specified. Start path: {start_path}"
            )
            return
        else:
            start_node = self.stage.node(start_path)

        exec_queue = start_node.build_execution_queue()
        return exec_queue

    def run(self, start_path: Node | str | pathlib.PurePosixPath | None = None):
        """Build queue and run it.

        Args:
            start_path: execution start path.

        """
        exec_queue = self.build_execution_queue(start_path=start_path)
        if not exec_queue:
            LOGGER.warning("No nodes found for execution.")
            return

        start_time = timeit.default_timer()
        success = True
        LOGGER.info(f"Executing graph (start path: {exec_queue[0]})")
        for node_path in exec_queue:
            try:
                self.stage.execute_node_from_path(node_path)
            except Exception:
                success = False
                LOGGER.error("Error raised during graph execution.")
                break
        if success:
            LOGGER.info(f"Executed graph in {timeit.default_timer() - start_time:.2f}s")
