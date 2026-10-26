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

    An existing input link on the target is replaced, and so is the output link of a
    source allowing a single one.
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

    def target_nodes(self):
        """list[Node]: nodes the command changes."""
        return [self.source_component.node, self.target_component.node]

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

    @property
    def replaced_link_uuids(self) -> list[UUID]:
        """list[UUID]: uuids of the existing links the command removes."""
        return list(self._unlink_command.link_uuids) if self._unlink_command else []

    def _build_child_unlink_command(self):
        """Create an unlink command for the links the new link replaces, if any.

        Those are the input link of the target and, when the source allows a
        single output link, its output link.
        """
        replaced = list(self.target_component.input_links)
        if self.source_component.single_output:
            replaced += self.source_component.output_links
        if not replaced:
            return

        # NOTE: Passing self as parent command to unlink command
        # It'll case pytest to segfault at post test garbage collection.
        # Instead manually call undo redo in appropriate time.
        self._unlink_command = UnlinkNodeComponentsCommand(
            stage=self.stage,
            link_uuids=[link.uuid for link in replaced],
        )

    def validate(self):
        """Check the components differ and are of the same type."""
        if self.target_component is self.source_component:
            raise NyxCommandValidationError("Can't connect component to itself")

        if not self.target_component.datatype.accepts(self.source_component.datatype):
            raise NyxCommandValidationError(
                "Can't connect components of different datatype: "
                f"{self.source_component} -> {self.target_component}"
            )
