import logging
import pathlib
from collections import OrderedDict
from collections.abc import Iterable

from PySide6 import QtCore
from PySide6 import QtGui

from nyx.core import Node
from nyx.core import Stage
from nyx.core.exceptions import NyxCommandValidationError
from ._base_nyx_command import NyxCommand
from ..plugin_subsystem.registry import NYX_REGISTRY

LOGGER = logging.getLogger(__name__)


class CreateNodeCommand(NyxCommand):
    def __init__(
        self,
        stage: Stage,
        node_name: str = "node",
        node_type_id: str = "core:node",
        parent_path: str | pathlib.PurePosixPath | None = None,
        position: QtCore.QPointF | Iterable = QtCore.QPointF(),
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        super().__init__(stage=stage, text="Create Node", parent=parent)
        if not isinstance(position, (QtCore.QPointF, QtCore.QPoint)):
            position = QtCore.QPointF(*position)

        self.position = position
        self.parent_path = (
            pathlib.PurePosixPath(parent_path) if parent_path else stage.ROOT_NODE_PATH
        )
        self.node_name = node_name
        self.node_type_id = node_type_id
        self.node_data: OrderedDict = None

    @property
    def node_path(self) -> str | None:
        return self.node_data.get("path")

    def redo(self) -> None:
        node = NYX_REGISTRY.get_node_cls(self.node_type_id)(name=self.node_name)
        self.stage.add_node(node, parent=self.parent_path)
        self.node_data = node.serialize()
        if self.position:
            node.set_position(self.position)

        self.setText(f"Create node ({node.path.as_posix()})")
        return super().redo()

    def undo(self) -> None:
        self.stage.delete_node(self.node_data.get("path"))
        self.node_data = None
        return super().undo()

    def validate(self):
        if self.parent_path:
            is_anchor = self.parent_path.as_posix() == self.parent_path.anchor
            if not is_anchor and not self.stage.node(self.parent_path):
                raise NyxCommandValidationError(
                    f"Invalid parent path: {self.parent_path}"
                )
