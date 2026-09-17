import logging
import pathlib
import typing
from collections import OrderedDict
from PySide6 import QtGui

from nyx.core import Node
from nyx.core.exceptions import NyxCommandValidationError
from ._base_nyx_command import NyxCommand
from ..plugin_subsystem.registry import NYX_REGISTRY

if typing.TYPE_CHECKING:
    from nyx.core.node_component._base_component import NodeComponent


LOGGER = logging.getLogger(__name__)


class DeleteNodeComponentCommand(NyxCommand):
    def __init__(
        self,
        node: Node,
        name: str | None = None,
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        super().__init__(
            stage=node.stage,
            text=f"Remove component from {node.cached_path}",
            parent=parent,
        )
        self.node_path = node.path
        self.name = name
        self.serialized_data: OrderedDict = OrderedDict()

    def redo(self) -> None:
        node = self.stage.node(self.node_path)
        component: NodeComponent = node[self.name]
        self.serialized_data = component.serialize()
        self.setText(
            f"Remove component ({self.node_path}.{self.name} ({component.type_id})"
        )
        node.components_model.remove_component(self.name)

        return super().redo()

    def undo(self) -> None:
        node = self.stage.node(self.node_path)
        component = node.components_model.create_component(
            type_id=self.serialized_data["type_id"]
        )
        component.deserialize(self.serialized_data)
        node.components_model.add_component(component)
        return super().undo()

    def validate(self):
        node = self.stage.node(self.node_path)
        if node is None:
            raise NyxCommandValidationError(
                "Target node doesn't exist %s:", str(self.node_path)
            )
