import dataclasses
import logging
import typing
from collections import OrderedDict
from PySide6 import QtGui

from ._base_nyx_command import NyxCommand
from .unlink_node_components import UnlinkNodeComponentsCommand
from ..node import Node
from ..node_component import NodeComponent
from ..contexts.serialization import NodeDeserializationContext
from ..exceptions import NyxCommandValidationError
from ...static.enums import RestoreUuidOption

if typing.TYPE_CHECKING:
    pass


LOGGER = logging.getLogger(__name__)


@dataclasses.dataclass
class DeletedComponentRecord:
    """Everything needed to restore one deleted component on undo."""

    component_name: str
    serialized_component_data: OrderedDict = dataclasses.field(
        default_factory=OrderedDict
    )
    was_component_expanded: bool = True
    model_row_before_deletion: int | None = None

    @property
    def component_uuid(self):
        """UUID: uuid of the deleted component."""
        return self.serialized_component_data[NodeComponent.UUID_KEY]


class DeleteNodeComponentCommand(NyxCommand):
    """Delete components from a node, unlinking their links first."""

    def __init__(
        self,
        node: Node,
        component_names: typing.Sequence[str],
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        """Initialize DeleteNodeComponentCommand.

        Args:
            node (Node): node owning the components.
            component_names (typing.Sequence[str]): names of components to delete.
            parent (QtGui.QUndoCommand | None): parent command.
        """
        self.node_uuid = node.uuid

        # Remove duplicates while preserving the order the caller gave us.
        self.component_names_to_delete: list[str] = list(
            OrderedDict.fromkeys(component_names)
        )

        self.deleted_component_records: list[DeletedComponentRecord] = [
            DeletedComponentRecord(component_name=component_name)
            for component_name in self.component_names_to_delete
        ]

        super().__init__(
            stage=node.stage,
            text="Delete components",
            parent=parent,
        )

        self._unlink_commands: list[UnlinkNodeComponentsCommand] = []

        self._build_child_unlink_commands()

    @property
    def deleted_component_uuids(self) -> list:
        """list: uuids of the components deleted by the command."""
        return [
            deleted_component_record.component_uuid
            for deleted_component_record in self.deleted_component_records
        ]

    def redo(self) -> None:
        """Unlink and delete the components, recording them for undo."""
        self._redo_unlink()
        node: Node = self.stage.get_object(self.node_uuid)

        removed_component_descriptions: list[str] = []

        for deleted_component_record in self.deleted_component_records:
            component: NodeComponent = node[deleted_component_record.component_name]

            deleted_component_record.serialized_component_data = component.serialize()
            deleted_component_record.was_component_expanded = component.is_expanded
            # Recorded immediately before removal, so the row already accounts
            # for any components removed earlier in this loop.
            deleted_component_record.model_row_before_deletion = component.row()

            removed_component_descriptions.append(
                f"{deleted_component_record.component_name} ({component.get_type_id()})"
            )

            node.components_model.remove_component(
                deleted_component_record.component_uuid
            )

        self.setText(
            f"Remove components ({node.path}: "
            f"{', '.join(removed_component_descriptions)})"
        )

        return super().redo()

    def undo(self) -> None:
        """Restore the deleted components and their links."""
        node: Node = self.stage.get_object(self.node_uuid)

        # Restore in reverse so each component returns to the row it had at the
        # moment it was removed.
        for deleted_component_record in reversed(self.deleted_component_records):
            deserialization_context = NodeDeserializationContext(
                stage=self.stage, entry_node=node, defer_links=False
            )
            restored_component = NodeComponent.deserialize(
                data=deleted_component_record.serialized_component_data,
                node=node,
                context=deserialization_context,
                component=None,
                restore_uuid=RestoreUuidOption.RESTORE,
            )
            node.components_model.add_component(
                restored_component,
                at_row=deleted_component_record.model_row_before_deletion,
            )
            restored_component.is_expanded = (
                deleted_component_record.was_component_expanded
            )

        result = super().undo()
        self._undo_unlink()
        return result

    def _redo_unlink(self) -> None:
        """Redo the unlink commands."""
        for unlink_command in self._unlink_commands:
            unlink_command.redo()

    def _undo_unlink(self) -> None:
        """Undo the unlink commands in reverse order."""
        for unlink_command in reversed(self._unlink_commands):
            unlink_command.undo()

    def _build_child_unlink_commands(self) -> None:
        """Create unlink commands for every link touching the deleted components."""
        node: Node = self.stage.get_object(self.node_uuid)

        # A link between two components that are both being deleted shows up on
        # each of them, so collect link uuids in an ordered, de-duplicated way
        # to avoid unlinking the same link twice.
        unique_link_uuids: OrderedDict = OrderedDict()

        for component_name in self.component_names_to_delete:
            component: NodeComponent = node[component_name]
            for link_uuid in list(component.links_uuids or []):
                unique_link_uuids[link_uuid] = None

        for link_uuid in unique_link_uuids:
            self._unlink_commands.append(
                UnlinkNodeComponentsCommand(stage=self.stage, link_uuids=[link_uuid])
            )

    def validate(self) -> None:
        """Check the node and all requested components exist."""
        node = self.stage.get_object(self.node_uuid)
        if node is None:
            raise NyxCommandValidationError(
                f"Target node doesn't exist: {self.node_uuid}"
            )

        if not self.component_names_to_delete:
            raise NyxCommandValidationError("No components were given to delete.")

        missing_component_names = [
            component_name
            for component_name in self.component_names_to_delete
            if node[component_name] is None
        ]
        if missing_component_names:
            raise NyxCommandValidationError(
                f"Components don't exist on node {node.path}: "
                f"{', '.join(missing_component_names)}"
            )
