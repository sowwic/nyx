import typing
import pathlib
from collections import deque

from nyx import get_main_logger

if typing.TYPE_CHECKING:
    from nyx.core import Node
    from nyx.core import Stage


LOGGER = get_main_logger()


class StageExecutor:

    def __repr__(self) -> str:
        return "Executor"

    def __init__(self, stage: "Stage") -> None:
        self.stage = stage

    def build_execution_queue(self,
                              start_path: "Node | str | pathlib.PurePosixPath | None" = None) -> "deque[pathlib.PurePosixPath]":
        """Build execution queue from given path.

        Args:
            start_path (Node | str | pathlib.PurePosixPath | None, optional): queue start path. Defaults to None.

        Returns:
            deque[pathlib.PurePosixPath]: resulting queue
        """
        start_path = self.stage.get_execution_start_path(start_path)
        if start_path is None:
            LOGGER.warning(f"{self} | No execution start path specified. Start path: {start_path}")
            return

        start_node = self.stage.get_node_from_absolute_path(start_path)
        exec_queue = start_node.build_execution_queue()

        return exec_queue

    def run(self,
            start_path: "Node | str | pathlib.PurePosixPath | None" = None):
        """Build queue and run it.

        Args:
            start_path ("Node | str | pathlib.PurePosixPath | None, optional): execution start path. Defaults to None.
        """
        queue = self.build_execution_queue(start_path=start_path)
        for node_path in queue:
            try:
                self.stage.execute_node_from_path(node_path)
            except Exception:
                LOGGER.error("Error raised during graph execution.")
                break
