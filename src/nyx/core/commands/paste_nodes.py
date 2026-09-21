import logging
import pathlib
from collections import OrderedDict
from collections import deque

from PySide6 import QtCore
from PySide6 import QtGui

from nyx.core import Node
from nyx.core import Stage
from nyx.core.exceptions import NyxCommandValidationError
from ._base_nyx_command import NyxCommand
from nyx.core.plugin_subsystem.registry import NYX_REGISTRY


LOGGER = logging.getLogger(__name__)


class PasteNodesCommand(NyxCommand):
    def __init__(
        self,
        stage: Stage,
        serialize_nodes: list[OrderedDict],
        position: QtCore.QPointF,
        parent_node: Node | pathlib.PurePosixPath | str | None = None,
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        super().__init__(stage, "Paste nodes", parent)
        self.serialized_nodes = serialize_nodes
        self.position = position
        self.created_node_paths = deque()
        self.parent_path = None

        if parent_node:
            self.parent_path = self.stage.pathify(parent_node)

    def redo(self) -> None:
        self.created_node_paths.clear()
        self.filter_serialized_nodes()

        for node_data in self.serialized_nodes:
            node_path = pathlib.PurePosixPath(node_data["path"])
            # Create new node and store it's path
            LOGGER.debug(f"Adding {node_path}")
            new_node_cls = NYX_REGISTRY.get_node_cls(node_data["type_id"])
            new_node = new_node_cls(name="__pasted_node__")
            self.stage.add_node(new_node, parent=self.parent_path)
            new_node.deserialize(node_data)
            paste_position = self.get_paste_position(new_node.position())
            new_node.set_position(paste_position)
            self.created_node_paths.append(new_node.cached_path)
        return super().redo()

    def undo(self) -> None:
        self.stage.delete_node(self.created_node_paths)
        return super().undo()

    def filter_serialized_nodes(self):
        """Filter out nodes that are already in the stage.

        If parent of copied node is about to be pasted child will be skipped
        to avoid duplication.
        """
        serialized_paths = [
            pathlib.PurePosixPath(node_data["path"])
            for node_data in self.serialized_nodes
        ]
        serialized_paths_set = set(serialized_paths)
        indexes_to_remove = []
        # Iterate over all serialized nodes and check
        # if any of their parents are about to be pasted
        for index, node_data in enumerate(self.serialized_nodes):
            node_path = pathlib.PurePosixPath(node_data["path"])
            # Check if parents of serialized node are serizalized as well.
            if set(node_path.parents).intersection(serialized_paths_set):
                LOGGER.debug(f"Skipping paste: {node_path}")
                indexes_to_remove.append(index)
        # Remove nodes that are about to be pasted as children
        for index in reversed(indexes_to_remove):
            self.serialized_nodes.pop(index)

    def get_paste_position(self, serialized_node_position: QtCore.QPointF):
        min_x, max_x, min_y, max_y = 10_000_000, -10_000_000, 10_000_000, -10_000_000
        pos_x = serialized_node_position.x()
        pos_y = serialized_node_position.y()
        min_x = min(pos_x, min_x)
        max_x = max(pos_x, max_x)
        min_y = min(pos_y, min_y)
        max_y = max(pos_y, max_y)

        new_x = self.position.x() + pos_x - min_x
        new_y = self.position.y() + pos_y - min_y
        return QtCore.QPointF(new_x, new_y)

    def validate(self):
        if self.parent_path:
            parent_node = self.stage.node(self.parent_path)
            if parent_node is None:
                raise NyxCommandValidationError(
                    f"Invalid parent path: {self.parent_path}"
                )
