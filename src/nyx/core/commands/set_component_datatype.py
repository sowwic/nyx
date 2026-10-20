import logging
from collections.abc import Iterator
from uuid import UUID

from PySide6 import QtGui

from nyx.core.exceptions import NyxCommandValidationError
from ._base_nyx_command import NyxCommand
from .unlink_node_components import UnlinkNodeComponentsCommand
from ..link import Link
from ..node_component import NodeComponent, NodeComponentLike
from ..plugin_subsystem.registry import NYX_REGISTRY
from ..stage import Stage

LOGGER = logging.getLogger(__name__)


class SetNodeComponentDatatypeCommand(NyxCommand):
    """Set the datatype hint of a component.

    A value the new datatype can't hold is replaced by the default of the datatype, and
    links that are no longer between compatible datatypes are removed. Undoing the
    command restores both.
    """

    def __init__(
        self,
        stage: Stage,
        node_component: NodeComponentLike,
        datatype_id: str,
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        """Initialize SetNodeComponentDatatypeCommand.

        Args:
            stage (Stage): target stage.
            node_component (NodeComponentLike): component to change.
            datatype_id (str): type id of the new datatype.
            parent (QtGui.QUndoCommand | None): parent command.
        """
        super().__init__(stage, "Set datatype", parent)
        component = self.stage.get_object(node_component, expected_type=NodeComponent)
        self.component_uuid = component.uuid
        self.old_datatype_id = component.datatype_id
        self.new_datatype_id = str(datatype_id)
        self.old_raw_value = component.raw_value
        self._unlink_command: UnlinkNodeComponentsCommand | None = None
        self.setText(f"{self.text()} ({component.path} -> {self.new_datatype_id})")

    @property
    def component(self) -> NodeComponent:
        """NodeComponent: component the command operates on."""
        return self.stage.get_object(self.component_uuid, expected_type=NodeComponent)

    @property
    def removed_link_uuids(self) -> list:
        """list[UUID]: uuids of the incompatible links the command removes."""
        return list(self._unlink_command.link_uuids) if self._unlink_command else []

    def validate(self) -> None:
        """Check the datatype of the component can be changed to the new one."""
        datatype = NYX_REGISTRY.get_datatype(self.new_datatype_id)
        if datatype is None:
            raise NyxCommandValidationError(f"Unknown datatype: {self.new_datatype_id}")
        if not datatype.selectable:
            raise NyxCommandValidationError(
                f"Datatype {datatype.display_name} can't be selected"
            )
        if self.component.is_datatype_locked:
            raise NyxCommandValidationError(
                f"Datatype of {self.component.path} is locked"
            )

    def redo(self) -> None:
        """Apply the new datatype, then fix the value and links it makes invalid."""
        component = self.component
        incompatible_before = self._incompatible_link_uuids()
        component.set_datatype(self.new_datatype_id)
        if not component.is_valid:
            component.push_value(component.datatype.create_default())
        self._build_child_unlink_command(skip=incompatible_before)
        if self._unlink_command:
            self._unlink_command.redo()
        return super().redo()

    def undo(self) -> None:
        """Restore the previous datatype and value, then the removed links."""
        component = self.component
        component.set_datatype(self.old_datatype_id)
        if component.raw_value != self.old_raw_value:
            component.push_value(self.old_raw_value)
        if self._unlink_command:
            self._unlink_command.undo()
        return super().undo()

    def _build_child_unlink_command(self, skip: set[UUID]) -> None:
        """Create an unlink command for the links that became incompatible, if any.

        Args:
            skip (set[UUID]): links that were incompatible before, left as they are.
        """
        incompatible = [
            link
            for link in self._iter_stage_links()
            if not link.is_datatype_compatible and link.uuid not in skip
        ]
        self._unlink_command = None
        if not incompatible:
            return

        # NOTE: Not parented to this command on purpose, see LinkNodeComponentsCommand.
        self._unlink_command = UnlinkNodeComponentsCommand(
            stage=self.stage, link_uuids=[link.uuid for link in incompatible]
        )

    def _incompatible_link_uuids(self) -> set[UUID]:
        """set[UUID]: uuids of the links that are incompatible right now."""
        return {
            link.uuid
            for link in self._iter_stage_links()
            if not link.is_datatype_compatible
        }

    def _iter_stage_links(self) -> Iterator[Link]:
        """Iterate over all links of the stage.

        The whole stage is checked, not only the links of the component: other
        components take their datatype from it, like a getter pointing at it.

        Yields:
            Link: registered link.
        """
        for stage_object in list(self.stage.uuid_map.values()):
            if isinstance(stage_object, Link):
                yield stage_object
