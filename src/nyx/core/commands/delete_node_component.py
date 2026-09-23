import logging
import typing
from collections import OrderedDict
from PySide6 import QtGui

from ._base_nyx_command import NyxCommand
from ..node import Node
from ..node_component import NodeComponent
from ..exceptions import NyxCommandValidationError

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
        super().__init__(
            stage=node.stage,
            text="Delete component",
            parent=parent,
        )

    def redo(self) -> None:
        node: Node = self.stage.get_object(self.node_uuid)
        component: NodeComponent = node[self.name]
        self.serialized_data = component.serialize()
        self.setText(
            f"Remove component ({node.path}.{self.name} ({component.get_type_id()})"
        )
        node.components_model.remove_component(self.name)

        return super().redo()

    def undo(self) -> None:
        node: Node = self.stage.get_object(self.node_uuid)
        component = NodeComponent.deserialize(
            data=self.serialized_data, component=None, restore_uuid=True
        )
        node.components_model.add_component(component)
        return super().undo()

    def validate(self):
        node = self.stage.get_object(self.node_uuid)
        if node is None:
            raise NyxCommandValidationError(
                "Target node doesn't exist %s:", str(self.node_uuid)
            )
