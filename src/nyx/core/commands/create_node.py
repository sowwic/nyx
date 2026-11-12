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
from ...static.enums import RestoreUuidOption

LOGGER = logging.getLogger(__name__)

if typing.TYPE_CHECKING:
    pass


class CreateNodeCommand(NyxCommand):
    """Create a node, or recreate one from serialized data."""

    MODIFIES_STRUCTURE = True

    def __init__(
        self,
        stage: Stage,
        name: str | None = None,
        type_id: str = "core:node",
        parent_node: NodeLike | None = None,
        position: QtCore.QPointF | Iterable = QtCore.QPointF(),
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        """Initialize CreateNodeCommand.

        Args:
            stage (Stage): target stage.
            name (str | None): node name.
            type_id (str): registered node type id.
            parent_node (NodeLike | None): parent node. Defaults to the stage root.
            position (QtCore.QPointF | Iterable): node position.
            parent (QtGui.QUndoCommand | None): parent command.
        """
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
        """Node: node created by the command."""
        return self.stage.get_object(self.node_data[Node.UUID_KEY], expected_type=Node)

    @property
    def parent_node(self) -> Node:
        """Node: parent of the created node."""
        return self.stage.get_object(self.parent_uuid, expected_type=Node)

    def target_nodes(self):
        """list[Node]: nodes the command changes."""
        return [self.stage.get_object(self.parent_uuid)]

    def redo(self) -> None:
        """Create the node, restoring serialized data on repeated calls."""
        self.node_name = NameValidator.get_valid_stage_object_name(self.node_name)
        if self.node_data:
            node = Node.deserialize(
                serialized_node=self.node_data,
                node=None,
                parent_node=self.parent_node,
                restore_uuid=RestoreUuidOption.ATTEMPT_RESTORE,
            )
        else:
            node: Node = self.stage.create_node(
                type_id=self.node_type_id, name=self.node_name, uuid=None
            )
            self.stage.add_node(node, parent=self.parent_path)

        self.node_data = node.serialize()
        if self.position:
            node.set_position(self.position)

        self.setText(f"Create node ({node.path.as_posix()})")
        return super().redo()

    def undo(self) -> None:
        """Delete the created node."""
        self.stage.delete_node(self.result_node)
        return super().undo()

    def validate(self):
        """Check the node type is registered and the parent exists."""
        if self.node_type_id not in NYX_REGISTRY.nodes.keys():
            raise NyxCommandValidationError(f"Invalid node type_id: {self.node_type_id}")

        if self.stage.get_object(self.parent_uuid) is None:
            raise NyxCommandValidationError(
                f"Invalid parent node UUID missing from stage: "
                f"{self.parent_uuid} ({self.parent_path})"
            )
