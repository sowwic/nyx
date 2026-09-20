import logging
import pathlib
import typing
from collections import OrderedDict
from collections.abc import Iterable

from PySide6 import QtCore
from PySide6 import QtGui

from nyx.core import Stage
from nyx.core.exceptions import NyxCommandValidationError
from ._base_nyx_command import NyxCommand
from ..plugin_subsystem.registry import NYX_REGISTRY
from ..name_validator import NameValidator

LOGGER = logging.getLogger(__name__)

if typing.TYPE_CHECKING:
    from nyx.core.node import Node


class CreateNodeCommand(NyxCommand):
    def __init__(
        self,
        stage: Stage,
        node_name: str | None = None,
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
            pathlib.PurePosixPath(parent_path) if parent_path else stage.root_node.path
        )
        self.node_name = node_name
        self.node_type_id = node_type_id
        self.node_data: OrderedDict = None

    @property
    def node_path(self) -> str | None:
        return self.node_data.get("path")

    @property
    def result_node(self) -> Node:
        return self.stage.node(self.node_path)

    def redo(self) -> None:
        node_cls = NYX_REGISTRY.get_node_cls(self.node_type_id)
        self.node_name = NameValidator.get_valid_stage_object_name(
            self.node_name or node_cls.DEFAULT_NAME
        )
        node = node_cls(name=self.node_name)
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
        if self.node_type_id not in NYX_REGISTRY.nodes.keys():
            raise NyxCommandValidationError(f"Invalid node type_id: {self.node_type_id}")

        if self.parent_path:
            is_anchor = self.parent_path.as_posix() == self.parent_path.anchor
            if not is_anchor and not self.stage.node(self.parent_path):
                raise NyxCommandValidationError(
                    f"Invalid parent path: {self.parent_path}"
                )
