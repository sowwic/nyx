import copy
import logging
from collections import OrderedDict
from collections import deque
from uuid import UUID

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
        restore_uuid=RestoreUuidOption.ATTEMPT_RESTORE,
    ) -> None:
        super().__init__(stage, "Paste nodes", parent)

        self.serialized_nodes = serialize_nodes
        self.position = position
        self.restore_uuid = restore_uuid
        self.parent_node_uuid = (
            self.stage.get_object(parent_node).uuid
            if parent_node
            else self.stage.root_node.uuid
        )

        # Results
        self.created_uuids: deque[UUID] = deque()
        # Nested identity captured on the very first redo(), one entry per
        # top-level serialized node. Each entry has the shape:
        #   {"uuid": UUID, "children": [<same shape>, ...]}
        # so that every node in the pasted subtree (not just the root) gets
        # the exact same UUID back whenever history is replayed.
        self._first_run_uuids: list[dict] = []

    @property
    def pasted_nodes(self):
        return [self.stage.get_object(uuid) for uuid in self.created_uuids]

    def redo(self) -> None:
        self.created_uuids.clear()
        parent_node = self.stage.get_object(self.parent_node_uuid)

        new_nodes = []
        for index, node_data in enumerate(self.serialized_nodes):
            LOGGER.debug("Pasting %s", node_data[Node.NAME_KEY])

            if self._first_run_uuids:
                # Replaying history: force the exact identities (including
                # every nested child) used the first time.
                node_data = copy.deepcopy(node_data)
                self._apply_uuids(node_data, self._first_run_uuids[index])

            new_node = Node.deserialize(
                serialized_node=node_data,
                node=None,
                parent_node=parent_node,
                restore_uuid=self.restore_uuid,
            )
            paste_position = self.get_paste_position(new_node.position())
            new_node.set_position(paste_position)
            self.created_uuids.append(new_node.uuid)
            new_nodes.append(new_node)

        if not self._first_run_uuids:
            # First time through: record whatever UUIDs were actually
            # assigned (restored or freshly generated) for the whole
            # subtree of each pasted node, so future replays are identical.
            self._first_run_uuids = [
                self._collect_uuids(new_node) for new_node in new_nodes
            ]
        return super().redo()

    def undo(self) -> None:
        self.stage.delete_node(self.created_uuids)
        self.created_uuids.clear()
        return super().undo()

    @staticmethod
    def _collect_uuids(node: Node) -> dict:
        """Recursively capture the UUID identity of `node` and all its
        descendants, in child order, after a (de)serialization pass.

        NOTE: assumes `node` exposes its children via `node.children`.
        Adjust the attribute/accessor name below if your `Node` API differs
        (e.g. `node.get_children()`).
        """
        return {
            "uuid": node.uuid,
            "children": [
                PasteNodesCommand._collect_uuids(child) for child in node.list_children()
            ],
        }

    @staticmethod
    def _apply_uuids(node_data: OrderedDict, uuid_record: dict) -> None:
        """Recursively force `node_data` (and its serialized children) to
        use the UUIDs captured in `uuid_record`, matching them up by
        position/order.
        """
        node_data[Node.UUID_KEY] = str(uuid_record["uuid"])

        children_data = node_data.get("children", [])
        children_records = uuid_record.get("children", [])

        if len(children_data) != len(children_records):
            # Structure mismatch between what was originally serialized and
            # what we recorded on first run - fail loudly rather than
            # silently mis-assigning identities.
            raise NyxCommandValidationError(
                "Serialized node children do not match the recorded "
                "history for this paste command; cannot safely replay "
                "UUIDs."
            )

        for child_data, child_record in zip(children_data, children_records):
            PasteNodesCommand._apply_uuids(child_data, child_record)

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
        if self.parent_node_uuid is not None:
            parent_node = self.stage.get_object(self.parent_node_uuid)
            if parent_node is None:
                raise NyxCommandValidationError(
                    f"Invalid parent node UUID: {self.parent_node_uuid}"
                )
