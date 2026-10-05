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


class DeleteNodeComponentCommand(NyxCommand):
    def __init__(
        self,
        node: Node,
        name: str | None = None,
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        self.node_uuid = node.uuid
        self.name = name
        self.serialized_data: OrderedDict = OrderedDict()
        self.expanded_state = True
        self.model_row = None

        super().__init__(
            stage=node.stage,
            text="Delete component",
            parent=parent,
        )

        self._unlink_commands: list[UnlinkNodeComponentsCommand] = []

        self._build_child_unlink_commands()

    @property
    def component_uuid(self):
        return self.serialized_data[NodeComponent.UUID_KEY]

    def redo(self) -> None:
        self._redo_unlink()
        node: Node = self.stage.get_object(self.node_uuid)
        component: NodeComponent = node[self.name]
        self.serialized_data = component.serialize()
        self.expanded_state = component.is_expanded
        self.model_row = component.row()

        self.setText(
            f"Remove component ({node.path}.{self.name} ({component.get_type_id()})"
        )
        node.components_model.remove_component(self.component_uuid)

        return super().redo()

    def undo(self) -> None:
        node: Node = self.stage.get_object(self.node_uuid)
        context = NodeDeserializationContext(
            stage=self.stage, entry_node=node, defer_links=False
        )
        component = NodeComponent.deserialize(
            data=self.serialized_data,
            node=node,
            context=context,
            component=None,
            restore_uuid=RestoreUuidOption.RESTORE,
        )
        node.components_model.add_component(component, at_row=self.model_row)
        component.is_expanded = self.expanded_state

        result = super().undo()
        self._undo_unlink()
        return result

    def _redo_unlink(self):
        for command in self._unlink_commands:
            command.redo()

    def _undo_unlink(self):
        for command in self._unlink_commands:
            command.undo()

    def _build_child_unlink_commands(self):
        node: Node = self.stage.get_object(self.node_uuid)
        component: NodeComponent = node[self.name]
        if not component.links_uuids:
            return
        for link_uuid in list(component.links_uuids):
            self._unlink_commands.append(
                UnlinkNodeComponentsCommand(stage=self.stage, link_uuid=link_uuid)
            )

    def validate(self):
        node = self.stage.get_object(self.node_uuid)
        if node is None:
            raise NyxCommandValidationError(
                "Target node doesn't exist %s:", str(self.node_uuid)
            )
