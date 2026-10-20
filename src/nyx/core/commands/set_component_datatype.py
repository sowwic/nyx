import logging

from PySide6 import QtGui

from nyx.core.exceptions import NyxCommandValidationError
from ._base_nyx_command import NyxCommand
from .unlink_node_components import UnlinkNodeComponentsCommand
from ..link import Link
from ..node_component import NodeComponent, NodeComponentLike
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
        """Check the datatype of the component can be changed."""
        if self.component.is_datatype_locked:
            raise NyxCommandValidationError(
                f"Datatype of {self.component.path} is locked"
            )

    def redo(self) -> None:
        """Apply the new datatype, then fix the value and links it makes invalid."""
        component = self.component
        component.set_datatype(self.new_datatype_id)
        if not component.is_valid:
            component.push_value(component.datatype.create_default())
        self._build_child_unlink_command()
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

    def _build_child_unlink_command(self) -> None:
        """Create an unlink command for the links that became incompatible, if any."""
        incompatible = self._collect_incompatible_links()
        self._unlink_command = None
        if not incompatible:
            return

        # NOTE: Not parented to this command on purpose, see LinkNodeComponentsCommand.
        self._unlink_command = UnlinkNodeComponentsCommand(
            stage=self.stage, link_uuids=[link.uuid for link in incompatible]
        )

    def _collect_incompatible_links(self) -> list[Link]:
        """Find the incompatible links of the component and of what inherits from it.

        Returns:
            list[Link]: links whose target doesn't accept the source datatype.
        """
        incompatible: list[Link] = []
        pending = [self.component]
        visited: set = set()
        while pending:
            current = pending.pop()
            if current.uuid in visited:
                continue
            visited.add(current.uuid)

            for link in current.links:
                if not link.is_datatype_compatible:
                    incompatible.append(link)
            pending.extend(
                link.target_component
                for link in current.output_links
                if link.target_component.get_datatype_source() is current
            )
        return incompatible
