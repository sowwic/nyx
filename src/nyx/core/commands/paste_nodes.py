import copy
import logging
from collections import OrderedDict
from collections import deque
from uuid import UUID

from PySide6 import QtCore
from PySide6 import QtGui

from ._base_nyx_command import NyxCommand
from .link_node_components import LinkNodeComponentsCommand
from ..node import Node, NodeLike
from ..node_component import NodeComponent
from ..contexts.serialization import NodeDeserializationContext
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
        self._link_pairs: list[tuple[UUID, UUID]] = []
        self._active_link_commands: list[LinkNodeComponentsCommand] = []

    @property
    def pasted_nodes(self) -> list[Node]:
        return [
            self.stage.get_object(uuid, expected_type=Node)
            for uuid in self.created_uuids
        ]

    def redo(self) -> None:
        self.created_uuids.clear()
        parent_node = self.stage.get_object(self.parent_node_uuid)
        first_run: bool = not self._first_run_uuids

        # One context for the whole paste, so links between different
        # top-level pasted nodes resolve against new copies

        restore_uuid = (
            self.restore_uuid if first_run else RestoreUuidOption.ATTEMPT_RESTORE
        )
        context = NodeDeserializationContext(stage=self.stage, defer_links=True)

        new_nodes = []
        for index, node_data in enumerate(self.serialized_nodes):
            LOGGER.debug("Pasting %s", node_data[Node.NAME_KEY])

            if not first_run:
                # Replaying history: force the exact identities (including
                # every nested child) used the first time.
                node_data = copy.deepcopy(node_data)
                self._apply_uuids(node_data, self._first_run_uuids[index])

            new_node = Node.deserialize(
                serialized_node=node_data,
                node=None,
                parent_node=parent_node,
                context=context,
                restore_uuid=restore_uuid,
            )
            paste_position = self.get_paste_position(new_node.position())
            new_node.set_position(paste_position)
            self.created_uuids.append(new_node.uuid)
            new_nodes.append(new_node)

        if first_run:
            # First time through: record whatever UUIDs were actually
            # assigned (restored or freshly generated) for the whole
            # subtree of each pasted node, so future replays are identical.
            self._first_run_uuids = [
                self._collect_uuids(new_node) for new_node in new_nodes
            ]

        result = super().redo()
        self._redo_links(context if first_run else None)
        return result

    def undo(self) -> None:
        for command in reversed(self._active_link_commands):
            command.undo()
        self._active_link_commands.clear()

        self.stage.delete_node(self.created_uuids)
        self.created_uuids.clear()
        return super().undo()

    @staticmethod
    def _collect_uuids(node: Node) -> dict:
        """Recursively capture the UUID identity of `node` and all its
        descendants, in child order, after a (de)serialization pass.
        """
        return {
            "uuid": node.uuid,
            "components": {
                component.name: component.uuid
                for component in node.components_model.list_components()
            },
            "children": [
                PasteNodesCommand._collect_uuids(child) for child in node.list_children()
            ],
        }

    @staticmethod
    def _apply_uuids(node_data: OrderedDict, record: dict) -> None:
        """Recursively force `node_data` (and its serialized children) to
        use the UUIDs captured in `uuid_record`, matching them up by
        position/order.
        """
        node_data[Node.UUID_KEY] = str(record["uuid"])

        for component_data in node_data.get(Node.COMPONENTS_KEY, []):
            component_uuid = record["components"].get(component_data["name"])
            if component_uuid is None:
                raise NyxCommandValidationError(
                    f"Component '{component_data['name']}' missing from paste history."
                )
            component_data[NodeComponent.UUID_KEY] = str(component_uuid)

        children_data = node_data.get(Node.CHILDREN_KEY, [])
        if len(children_data) != len(record["children"]):
            raise NyxCommandValidationError(
                "Serialized children do not match the recorded paste history."
            )
        for child_data, child_record in zip(children_data, record["children"]):
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

    def _redo_links(self, context: NodeDeserializationContext | None) -> None:
        """First run: derive links from the context and validate each one.
        Replays: re-run exactly the links accepted the first time."""
        self._active_link_commands.clear()
        first_run = context is not None
        candidates = context.resolved_links() if first_run else self._link_pairs

        accepted: list[tuple[UUID, UUID]] = []
        for src_uuid, tgt_uuid in candidates:
            source = self.stage.get_object(src_uuid)
            target = self.stage.get_object(tgt_uuid)
            if source is None or target is None:
                continue

            # Built fresh each redo, so it never holds stale component objects
            command = LinkNodeComponentsCommand(
                stage=self.stage, source=source, target=target
            )
            if first_run:
                try:
                    command.validate()
                except NyxCommandValidationError:
                    LOGGER.warning("Skipping paste link %s -> %s", source, target)
                    continue
            command.redo()
            self._active_link_commands.append(command)
            accepted.append((src_uuid, tgt_uuid))

        if first_run:
            self._link_pairs = accepted
