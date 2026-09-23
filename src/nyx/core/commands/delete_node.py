import logging
import typing
from uuid import UUID
from collections import deque
from collections.abc import Sequence

from PySide6 import QtGui

from ..stage import Stage
from ._base_nyx_command import NyxCommand
from ..node import Node, NodeLike
from ..exceptions import NyxCommandValidationError
from ...static.enums import RestoreUuidOption

LOGGER = logging.getLogger(__name__)

if typing.TYPE_CHECKING:
    from ..stage import Stage


class DeleteNodeCommand(NyxCommand):
    def __init__(
        self,
        stage: Stage,
        nodes: Sequence[NodeLike] | NodeLike,
        command_text: str = "Delete node",
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        super().__init__(stage=stage, text=command_text, parent=parent)
        if not isinstance(nodes, Sequence):
            nodes = [nodes]

        self.requested_nodes = nodes
        self.parents_map = {}
        self.deleted_uuids = deque()
        self.serialized_nodes = deque()

    def redo(self) -> None:
        nodes_to_delete = [self.stage.get_object(node) for node in self.requested_nodes]
        for each_node in nodes_to_delete:
            self.serialized_nodes.append(each_node.serialize())

        if len(nodes_to_delete) == 1:
            self.setText(f"Delete node ({nodes_to_delete[-1].path.as_posix()})")
        else:
            self.setText("Deleted nodes")

        self.deleted_uuids.clear()

        top_level_nodes = self.stage.filter_top_level_nodes(nodes_to_delete)
        self.deleted_uuids = [node.uuid for node in top_level_nodes]
        self.parents_uuids_map = {
            node.uuid: node.parent().uuid for node in top_level_nodes
        }
        self.stage.delete_node(self.deleted_uuids)
        return super().redo()

    def undo(self) -> None:
        for node_data in self.serialized_nodes:
            node_uuid = UUID(node_data[Node.UUID_KEY])
            if node_uuid not in self.deleted_uuids:
                continue

            parent_node = self.stage.get_object(self.parents_uuids_map[node_uuid])

            Node.deserialize(
                serialized_node=node_data,
                node=None,
                parent_node=parent_node,
                restore_uuid=RestoreUuidOption.RESTORE,
            )

        self.serialized_nodes.clear()
        self.parents_map.clear()
        self.deleted_uuids.clear()
        return super().undo()

    def validate(self):
        nodes_to_delete = [
            self.stage.get_object(node_like) for node_like in self.requested_nodes
        ]
        status = all([node is not None for node in nodes_to_delete])
        if not status:
            raise NyxCommandValidationError(
                f"Invalid requested nodes for deletion: {self.requested_nodes}"
            )
