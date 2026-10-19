import typing
import logging
from uuid import UUID

from PySide6 import QtGui

from nyx.core.exceptions import NyxCommandValidationError
from ._base_nyx_command import NyxCommand
from .unlink_node_components import UnlinkNodeComponentsCommand

if typing.TYPE_CHECKING:
    from ..link import Link
    from ..stage import Stage
    from ..node_component import NodeComponent, NodeComponentLike

LOGGER = logging.getLogger(__name__)


class LinkNodeComponentsCommand(NyxCommand):
    """Link a source component to a target component.

    An existing input link on the target is replaced.
    """

    def __init__(
        self,
        stage: Stage,
        source: NodeComponentLike,
        target: NodeComponentLike,
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        """Initialize LinkNodeComponentsCommand.

        Args:
            stage (Stage): target stage.
            source (NodeComponentLike): source component.
            target (NodeComponentLike): target component.
            parent (QtGui.QUndoCommand | None): parent command.
        """
        super().__init__(stage=stage, text="Link components", parent=parent)
        self.source_component_uuid: UUID = self.stage.get_object(source).uuid
        self.target_component_uuid: UUID = self.stage.get_object(target).uuid

        self._unlink_command = None
        self._link_uuid: UUID | None = None

        self._build_child_unlink_command()

    @property
    def result_link(self) -> Link:
        """Link: link created by the command."""
        return self.stage.get_object(self._link_uuid)

    @property
    def result_link_uuid(self) -> UUID:
        """UUID: uuid of the link created by the command."""
        return self._link_uuid

    @property
    def source_component(self) -> NodeComponent:
        """NodeComponent: link source."""
        return self.stage.get_object(self.source_component_uuid)

    @property
    def target_component(self) -> NodeComponent:
        """NodeComponent: link target."""
        return self.stage.get_object(self.target_component_uuid)

    def redo(self) -> None:
        """Create the link, removing the target's previous input link."""
        if self._unlink_command:
            self._unlink_command.redo()

        result_link = self.stage.link_components(
            source_component=self.source_component,
            target_component=self.target_component,
            use_uuid=self._link_uuid,
        )
        self._link_uuid = result_link.uuid

        self.setText(f"Link components: {result_link.path_connection_str}")
        return super().redo()

    def undo(self) -> None:
        """Remove the link and restore the replaced one."""
        self.stage.unregister_link(self._link_uuid)
        if self._unlink_command:
            self._unlink_command.undo()
        return super().undo()

    def _build_child_unlink_command(self):
        """Create an unlink command for the target's existing input link, if any."""
        target_component = self.target_component
        target_input_links = target_component.input_links
        if not target_input_links:
            return

        existing_link = target_input_links[0]

        # NOTE: Passing self as parent command to unlink command
        # It'll case pytest to segfault at post test garbage collection.
        # Instead manually call undo redo in appropriate time.
        self._unlink_command = UnlinkNodeComponentsCommand(
            stage=self.stage,
            link_uuids=[existing_link.uuid],
        )

    def validate(self):
        """Check the components differ and are of the same type."""
        if self.target_component is self.source_component:
            raise NyxCommandValidationError("Can't connect component to itself")

        if not isinstance(self.target_component, type(self.source_component)):
            raise NyxCommandValidationError(
                "Can't connect components of different type: "
                f"{self.source_component} -> {self.target_component}"
            )
