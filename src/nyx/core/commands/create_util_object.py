import logging
import typing
from collections import OrderedDict

from PySide6 import QtCore, QtGui

from ._base_nyx_command import NyxCommand
from ..exceptions import NyxCommandValidationError
from ..node import Node, NodeLike
from ..plugin_subsystem.registry import NYX_REGISTRY
from ..stage import Stage
from ..util_object import UtilObject
from ...static.enums import RestoreUuidOption

LOGGER = logging.getLogger(__name__)


class CreateUtilObjectCommand(NyxCommand):
    """Create a util object in a node, or recreate one from serialized data."""

    def __init__(
        self,
        stage: Stage,
        type_id: str,
        node: NodeLike | None = None,
        position: QtCore.QPointF | typing.Iterable[float] = (0.0, 0.0),
        size: QtCore.QSizeF | typing.Iterable[float] | None = None,
        properties: typing.Mapping[str, typing.Any] | None = None,
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        """Initialize CreateUtilObjectCommand.

        Args:
            stage (Stage): target stage.
            type_id (str): registered util object type id.
            node (NodeLike | None): node to add the object to. Defaults to the root.
            position (QtCore.QPointF | typing.Iterable[float]): top left corner.
            size (QtCore.QSizeF | typing.Iterable[float] | None): size, the default of
                the type if omitted.
            properties (typing.Mapping[str, typing.Any] | None): more properties of
                the object, such as the text of a note.
            parent (QtGui.QUndoCommand | None): parent command.
        """
        super().__init__(stage=stage, text="Create util object", parent=parent)
        self.type_id = type_id
        owner = (
            self.stage.get_object(node, expected_type=Node)
            if node
            else self.stage.root_node
        )
        self.node_uuid = owner.uuid
        self.properties = dict(properties or {})
        self.properties[UtilObject.POSITION_KEY] = _as_list(position)
        if size is not None:
            self.properties[UtilObject.SIZE_KEY] = _as_list(size)
        self.object_data: OrderedDict | None = None

    @property
    def node(self) -> Node:
        """Node: node the object is added to."""
        return self.stage.get_object(self.node_uuid, expected_type=Node)

    @property
    def result_object(self) -> UtilObject:
        """UtilObject: object created by the command."""
        return self.stage.get_object(
            self.object_data[UtilObject.UUID_KEY], expected_type=UtilObject
        )

    def target_nodes(self):
        """list[Node]: nodes the command changes."""
        return [self.node]

    def validate(self) -> None:
        """Check the type is registered and the node allows util objects."""
        if self.type_id not in NYX_REGISTRY.util_objects:
            raise NyxCommandValidationError(
                f"Invalid util object type_id: {self.type_id}"
            )
        if self.node.locks_children:
            raise NyxCommandValidationError(f"{self.node.path} owns its contents")

    def redo(self) -> None:
        """Create the object, restoring serialized data on repeated calls."""
        if self.object_data:
            util_object = UtilObject.deserialize(
                node=self.node,
                serialized_data=self.object_data,
                restore_uuid=RestoreUuidOption.RESTORE,
            )
        else:
            util_object = NYX_REGISTRY.get_util_object_cls(self.type_id)()
            util_object.apply_properties(self.properties)
            self.node.add_util_object(util_object)
            self.object_data = util_object.serialize()

        self.setText(f"Create {util_object.get_type_display_name().lower()}")
        return super().redo()

    def undo(self) -> None:
        """Remove the created object."""
        self.node.remove_util_object(self.result_object)
        return super().undo()


def _as_list(value) -> list[float]:
    if isinstance(value, (QtCore.QPointF, QtCore.QPoint)):
        return [value.x(), value.y()]
    if isinstance(value, (QtCore.QSizeF, QtCore.QSize)):
        return [value.width(), value.height()]
    return list(value)
