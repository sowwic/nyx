import logging
import pathlib
from collections import deque
from collections.abc import Sequence

from PySide6 import QtGui

from nyx.core import Node
from nyx.core import Stage
from nyx.core.exceptions import NyxCommandValidationError
from nyx.core.plugin_subsystem.registry import NYX_REGISTRY
from ._base_nyx_command import NyxCommand

LOGGER = logging.getLogger(__name__)


class DeleteNodeCommand(NyxCommand):
    def __init__(
        self,
        stage: Stage,
        nodes: list[Node | pathlib.PurePosixPath | str],
        command_text: str = "Delete node",
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        super().__init__(stage=stage, text=command_text, parent=parent)
        if not isinstance(nodes, Sequence):
            nodes = [nodes]

        self.nodes_to_delete = [self.stage.pathify(node) for node in nodes]
        self.serialized_nodes = deque()
        self.deleted_paths = deque()

    def redo(self) -> None:
        nodes = [self.stage.node(node) for node in self.nodes_to_delete]
        for each_node in nodes:
            self.serialized_nodes.append(each_node.serialize())

        if len(nodes) == 1:
            self.setText(f"Delete node ({nodes[-1].path.as_posix()})")
        else:
            self.setText("Deleted nodes")

        self.deleted_paths.clear()
        serialized_paths = [
            pathlib.PurePosixPath(node_data.get("path"))
            for node_data in self.serialized_nodes
        ]
        serialized_paths_set = set(serialized_paths)

        # Filter paths to delete, so that only parent paths are deleted.
        for path in serialized_paths:
            if set(path.parents).intersection(serialized_paths_set):
                continue
            self.deleted_paths.append(path)

        self.stage.delete_node(self.deleted_paths)
        return super().redo()

    def undo(self) -> None:
        for node_data in self.serialized_nodes:
            node_path: pathlib.PurePosixPath = pathlib.PurePosixPath(
                node_data.get("path")
            )
            if node_path not in self.deleted_paths:
                continue
            parent_path = node_path.parent
            new_node_cls = NYX_REGISTRY.get_node_cls(node_data["type_id"])
            new_node = new_node_cls()
            self.stage.add_node(new_node, parent=parent_path)
            new_node.deserialize(node_data)
        self.serialized_nodes.clear()
        return super().undo()

    def validate(self):
        nodes_to_delete = [self.stage.node(node) for node in self.nodes_to_delete]
        status = all([node is not None for node in nodes_to_delete])
        if not status:
            raise NyxCommandValidationError(
                f"Invalid node paths: {self.nodes_to_delete}"
            )
