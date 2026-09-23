import logging
from PySide6 import QtGui

from ._base_nyx_command import NyxCommand
from ..node import Node
from ..node_component import NodeComponent
from ..exceptions import NyxCommandValidationError
from ..plugin_subsystem.registry import NYX_REGISTRY
from ..name_validator import NameValidator

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
        self.node_uuid = node.uuid
        self.component_uuid = None
        self.type_id = type_id
        self.name = name

    @property
    def result_component(self) -> NodeComponent:
        return self.stage.get_object(self.component_uuid)

    def redo(self) -> None:
        node = self.stage.get_object(self.node_uuid)
        component = node.components_model.create_component(self.type_id)
        self.name = NameValidator.get_valid_stage_object_name(
            self.name or component.DEFAULT_NAME
        )
        component.name = self.name
        node.components_model.add_component(component)
        self.component_uuid = component.uuid

        self.setText(f"Add component ({node.path}.{component.name} ({self.type_id})")
        return super().redo()

    def undo(self) -> None:
        node = self.stage.get_object(self.node_uuid)
        node.components_model.remove_component(self.component_uuid)
        return super().undo()

    def validate(self):
        node = self.stage.get_object(self.node_uuid)
        if node is None:
            raise NyxCommandValidationError(
                "Target node doesn't exist %s:", str(self.node_uuid)
            )

        if self.type_id not in NYX_REGISTRY.node_components.keys():
            raise NyxCommandValidationError("Invalid type_id: %s", self.type_id)
