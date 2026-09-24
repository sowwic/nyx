import logging
import typing
from collections import OrderedDict
from collections.abc import Iterable

from PySide6 import QtCore
from PySide6 import QtGui

from ._base_nyx_command import NyxCommand
from ..node import Node, NodeLike
from ..stage import Stage
from ..exceptions import NyxCommandValidationError
from ..plugin_subsystem.registry import NYX_REGISTRY
from ..name_validator import NameValidator

LOGGER = logging.getLogger(__name__)

if typing.TYPE_CHECKING:
    pass


class CreateNodeCommand(NyxCommand):
    def __init__(
        self,
        stage: Stage,
        name: str | None = None,
        type_id: str = "core:node",
        parent_node: NodeLike | None = None,
        position: QtCore.QPointF | Iterable = QtCore.QPointF(),
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        super().__init__(stage=stage, text="Create Node", parent=parent)
        if not isinstance(position, (QtCore.QPointF, QtCore.QPoint)):
            position = QtCore.QPointF(*position)

        found_parent_node: Node = (
            self.stage.get_object(parent_node) if parent_node else self.stage.root_node
        )

        if not found_parent_node:
            raise ValueError(f"Parent node doesn't exist: {parent_node}")

        self.parent_path = found_parent_node.path
        self.parent_uuid = found_parent_node.uuid
        self.position = position
        self.node_name = name or NYX_REGISTRY.get_node_cls(type_id).DEFAULT_NAME
        self.node_type_id = type_id
        self.node_data: OrderedDict = None

    @property
    def result_node(self) -> Node:
        return self.stage.get_object(self.node_data[Node.UUID_KEY])

    def redo(self) -> None:
        self.node_name = NameValidator.get_valid_stage_object_name(self.node_name)
        uuid = self.node_data.get(Node.UUID_KEY) if self.node_data else None
        node: Node = self.stage.create_node(
            type_id=self.node_type_id, name=self.node_name, uuid=uuid
        )

        self.stage.add_node(node, parent=self.parent_path)
        self.node_data = node.serialize()
        if self.position:
            node.set_position(self.position)

        self.setText(f"Create node ({node.path.as_posix()})")
        return super().redo()

    def undo(self) -> None:
        self.stage.delete_node(self.result_node)
        return super().undo()

    def validate(self):
        if self.node_type_id not in NYX_REGISTRY.nodes.keys():
            raise NyxCommandValidationError(f"Invalid node type_id: {self.node_type_id}")

        if self.stage.get_object(self.parent_uuid) is None:
            raise NyxCommandValidationError(
                f"Invalid parent node UUID missing from stage: "
                f"{self.parent_uuid} ({self.parent_path})"
            )
