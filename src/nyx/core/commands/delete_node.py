import logging
import typing
from uuid import UUID
from collections import deque
from collections.abc import Sequence

from PySide6 import QtGui

from ..stage import Stage
from ._base_nyx_command import NyxCommand
from .unlink_node_components import UnlinkNodeComponentsCommand
from ..contexts.serialization import NodeDeserializationContext
from ..node import Node, NodeLike
from ...static.enums import RestoreUuidOption

LOGGER = logging.getLogger(__name__)

if typing.TYPE_CHECKING:
    from ..stage import Stage


class DeleteNodeCommand(NyxCommand):
    """Delete one or more nodes, unlinking their components first."""

    def __init__(
        self,
        stage: Stage,
        nodes: Sequence[NodeLike] | NodeLike,
        command_text: str = "Delete node",
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        """Initialize DeleteNodeCommand.

        Args:
            stage (Stage): target stage.
            nodes (Sequence[NodeLike] | NodeLike): nodes to delete.
            command_text (str): undo stack text.
            parent (QtGui.QUndoCommand | None): parent command.
        """
        super().__init__(stage=stage, text=command_text, parent=parent)
        if not isinstance(nodes, Sequence):
            nodes = [nodes]

        self.requested_nodes = [self.stage.pathify(node) for node in nodes]
        self.parents_map = {}
        self.deleted_uuids = deque()
        self.serialized_nodes = deque()
        self._component_unlink_commands: list[UnlinkNodeComponentsCommand] = []

        self._build_child_unlink_commands()

    def redo(self) -> None:
        """Unlink and delete the nodes, serializing them for undo."""
        self._redo_unlink()
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
        """Restore the deleted nodes and their links."""
        for node_data in self.serialized_nodes:
            node_uuid = UUID(node_data[Node.UUID_KEY])
            if node_uuid not in self.deleted_uuids:
                continue

            parent_node = self.stage.get_object(self.parents_uuids_map[node_uuid])
            context = NodeDeserializationContext(
                stage=self.stage, entry_node=None, defer_links=True
            )
            Node.deserialize(
                serialized_node=node_data,
                node=None,
                parent_node=parent_node,
                context=context,
                restore_uuid=RestoreUuidOption.RESTORE,
            )

        self.serialized_nodes.clear()
        self.parents_map.clear()
        self.deleted_uuids.clear()

        result = super().undo()

        self._undo_unlink()
        return result

    def _build_child_unlink_commands(self):
        """Create unlink commands for every link touching the deleted nodes."""
        links_to_unlink = set()
        for node_path in self.requested_nodes:
            node = self.stage.get_object(node_path, expected_type=Node)
            collected_links = self.stage.collect_links(from_node=node)
            if not collected_links:
                continue
            for link in collected_links:
                links_to_unlink.add(link.uuid)

        for link_uuid in list(links_to_unlink):
            unlink_command = UnlinkNodeComponentsCommand(
                stage=self.stage, link_uuids=[link_uuid]
            )
            self._component_unlink_commands.append(unlink_command)

    def _redo_unlink(self):
        """Redo the unlink commands."""
        for unlink_commad in self._component_unlink_commands:
            unlink_commad.redo()

    def _undo_unlink(self):
        """Undo the unlink commands."""
        for unlink_command in self._component_unlink_commands:
            unlink_command.undo()
