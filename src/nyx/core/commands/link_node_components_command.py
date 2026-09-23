import typing
import logging
import pathlib

from PySide6 import QtGui

from nyx.core.exceptions import NyxCommandValidationError
from ._base_nyx_command import NyxCommand

if typing.TYPE_CHECKING:
    from ..stage import Stage
    from ..node_component import NodeComponent

LOGGER = logging.getLogger(__name__)


class LinkNodeComponentsCommand(NyxCommand):
    def __init__(
        self,
        stage: Stage,
        source_component: NodeComponent | pathlib.PurePosixPath | str,
        destination_component: NodeComponent | pathlib.PurePosixPath | str,
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        super().__init__(stage=stage, text="Link components", parent=parent)
        self.source_component_path = self.stage.pathify(source_component)
        self.destination_component_path = self.stage.pathify(destination_component)

        self.source_component_previous_value = self.stage.get_object(
            source_component
        ).value

    def redo(self) -> None:
        # node = self.stage.get_object(self.node_path)
        # self.setText(f"Add component ({node.path}.{component.name} ({self.type_id})")
        return super().redo()

    def undo(self) -> None:
        # node = self.stage.get_object(self.node_path)
        # node.components_model.remove_component(self.name)
        return super().undo()

    def validate(self):
        source_component = self.stage.get_object(self.source_component_path)
        destination_component = self.stage.get_object(
            self.destination_component_path
        )
        if not isinstance(destination_component, type(source_component)):
            raise NyxCommandValidationError("Can't connect to destination")
        # node = self.stage.get_object(self.node_path)
        # if node is None:
        #     raise NyxCommandValidationError(
        #         "Target node doesn't exist %s:", str(self.node_path)
        #     )
        #
        # if self.type_id not in NYX_REGISTRY.node_components.keys():
        #     raise NyxCommandValidationError("Invalid type_id: %s", self.type_id)
