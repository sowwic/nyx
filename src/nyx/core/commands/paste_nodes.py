import logging
from collections import OrderedDict
from collections import deque

from PySide6 import QtCore
from PySide6 import QtGui

from ._base_nyx_command import NyxCommand
from ..node import Node, NodeLike
from ..stage import Stage
from ..exceptions import NyxCommandValidationError
from ...static.enums import RestoreUuidOption


LOGGER = logging.getLogger(__name__)


class PasteNodesCommand(NyxCommand):
    def __init__(
        self,
        stage: Stage,
        serialize_nodes: list[OrderedDict],
        position: QtCore.QPointF,
        parent_node: NodeLike | None = None,
        parent: QtGui.QUndoCommand | None = None,
        restore_uuid=RestoreUuidOption.GENERATE_NEW,
    ) -> None:
        super().__init__(stage, "Paste nodes", parent)
        self.serialized_nodes = serialize_nodes
        self.position = position
        self.created_uuids = deque()
        self.parent_node_uuid = None
        self.restore_uuid = restore_uuid

        self.parent_node_uuid = (
            self.stage.get_object(parent_node).uuid
            if parent_node
            else self.stage.root_node.uuid
        )

    def redo(self) -> None:
        self.created_uuids.clear()
        # self.filter_serialized_nodes()
        parent_node = self.stage.get_object(self.parent_node_uuid)

        for node_data in self.serialized_nodes:
            # Create new node and store it's path
            LOGGER.debug("Pasting %s", node_data[Node.NAME_KEY])
            new_node = Node.deserialize(
                serialized_node=node_data,
                node=None,
                parent_node=parent_node,
                restore_uuid=self.restore_uuid,
            )
            paste_position = self.get_paste_position(new_node.position())
            new_node.set_position(paste_position)
            self.created_uuids.append(new_node.uuid)
        return super().redo()

    def undo(self) -> None:
        self.stage.delete_node(self.created_uuids)
        self.created_uuids.clear()
        return super().undo()

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
        parent_node = self.stage.get_object(self.parent_node_uuid)
        if parent_node is None:
            raise NyxCommandValidationError(
                f"Invalid parent node UUID: {self.parent_node_uuid}"
            )
