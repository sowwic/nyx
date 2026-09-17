import logging
from PySide6 import QtGui

from nyx.core import Node
from nyx.core.exceptions import NyxCommandValidationError
from ._base_nyx_command import NyxCommand
from ..plugin_subsystem.registry import NYX_REGISTRY

LOGGER = logging.getLogger(__name__)


class AddNodeComponentCommand(NyxCommand):
    def __init__(
        self,
        node: Node,
        type_id: str,
        name: str | None = None,
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        super().__init__(
            stage=node.stage, text=f"Add component {type_id}", parent=parent
        )
        self.node_path = node.path
        self.type_id = type_id
        self.name = name

    def redo(self) -> None:
        node = self.stage.node(self.node_path)
        component = node.components_model.create_component(self.type_id)
        self.name = self.name or component.DEFAULT_NAME
        component.name = self.name
        node.components_model.add_component(component)

        self.setText(f"Add component ({node.path}.{component.name} ({self.type_id})")
        return super().redo()

    def undo(self) -> None:
        node = self.stage.node(self.node_path)
        node.components_model.remove_component(self.name)
        return super().undo()

    def validate(self):
        node = self.stage.node(self.node_path)
        if node is None:
            raise NyxCommandValidationError(
                "Target node doesn't exist %s:", str(self.node_path)
            )

        if self.type_id not in NYX_REGISTRY.node_components.keys():
            raise NyxCommandValidationError("Invalid type_id: %s", self.type_id)
