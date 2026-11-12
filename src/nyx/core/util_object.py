import logging
import pathlib
import typing
from collections import OrderedDict
from uuid import UUID

from PySide6 import QtCore, QtGui

from .layered_config import get_app_config
from .plugin_subsystem.registry import NYX_REGISTRY
from .stage_object import StageObject
from ..static.enums import RestoreUuidOption

if typing.TYPE_CHECKING:
    from .contexts.serialization import NodeDeserializationContext
    from .node import Node
    from .stage import Stage

LOGGER = logging.getLogger(__name__)


class UtilObject(StageObject):
    """Base class of the objects that help organizing a node, like notes and groups.

    A util object belongs to a node and is drawn in the graph of the node, next to the
    child nodes. It isn't part of the execution and it has no components or links.
    Util objects are serialized in the `util_objects` list of their node.

    Subclasses define the type by overriding the `get_type_*` classmethods. The state
    they add is exposed as properties (`serialize_properties`), so it can be saved,
    changed and restored by commands.
    """

    TYPE_ID_KEY = "type_id"
    POSITION_KEY = "position"
    SIZE_KEY = "size"

    DEFAULT_SIZE: tuple[float, float] = (200.0, 120.0)
    MIN_SIZE: tuple[float, float] = (40.0, 24.0)

    def __init__(self, uuid: UUID | str | None = None):
        """Initialize UtilObject.

        Args:
            uuid (UUID | str | None): object uuid. Generated if omitted.
        """
        super().__init__(uuid=uuid)
        self._node: Node | None = None
        self._position = QtCore.QPointF()
        self._size = QtCore.QSizeF(*self.DEFAULT_SIZE)

    def __repr__(self) -> str:
        """str: class name and the uuid."""
        return f"{self.__class__.__name__} ({self.uuid})"

    @property
    def node(self) -> Node | None:
        """Node | None: node owning the object, None until it is added to one."""
        return self._node

    @property
    def stage(self) -> Stage | None:
        """Stage | None: stage of the owning node."""
        return None if self._node is None else self._node.stage

    @property
    def path(self) -> pathlib.PurePosixPath:
        """pathlib.PurePosixPath: path of the owning node plus an id of the object."""
        return self._node.path / f"@{self.get_type_id()}-{str(self.uuid)[:8]}"

    @property
    def is_locked(self) -> bool:
        """bool: the object can't be changed, because its node is owned by another."""
        node = self._node
        return node is not None and (node.locks_children or node.is_in_locked_scope)

    @property
    def position(self) -> QtCore.QPointF:
        """QtCore.QPointF: top left corner in the scene of the owning node."""
        return QtCore.QPointF(self._position)

    @position.setter
    def position(self, value: QtCore.QPointF | typing.Iterable[float]):
        self._position = _as_point(value)

    @property
    def size(self) -> QtCore.QSizeF:
        """QtCore.QSizeF: size in the scene, never smaller than `MIN_SIZE`."""
        return QtCore.QSizeF(self._size)

    @size.setter
    def size(self, value: QtCore.QSizeF | typing.Iterable[float]):
        size = _as_size(value)
        self._size = QtCore.QSizeF(
            max(size.width(), self.MIN_SIZE[0]), max(size.height(), self.MIN_SIZE[1])
        )

    @property
    def rect(self) -> QtCore.QRectF:
        """QtCore.QRectF: area of the object in the scene of the owning node."""
        return QtCore.QRectF(self._position, self._size)

    def serialize_properties(self) -> OrderedDict[str, typing.Any]:
        """Get the state of the object that commands can change.

        Returns:
            OrderedDict[str, typing.Any]: serializable values by name. Subclasses add
                their own.
        """
        properties = OrderedDict()
        properties[self.POSITION_KEY] = [self._position.x(), self._position.y()]
        properties[self.SIZE_KEY] = [self._size.width(), self._size.height()]
        return properties

    def apply_properties(self, properties: typing.Mapping[str, typing.Any]) -> None:
        """Set the state of the object. Missing names are left unchanged.

        Args:
            properties (typing.Mapping[str, typing.Any]): values by name, as returned
                by `serialize_properties`.
        """
        if self.POSITION_KEY in properties:
            self.position = properties[self.POSITION_KEY]
        if self.SIZE_KEY in properties:
            self.size = properties[self.SIZE_KEY]

    def serialize(self) -> OrderedDict[str, typing.Any]:
        """Serialize the object.

        Returns:
            OrderedDict[str, typing.Any]: serialized data.
        """
        serialized_data = super().serialize()
        serialized_data[self.TYPE_ID_KEY] = self.get_type_id()
        serialized_data.update(self.serialize_properties())
        return serialized_data

    @classmethod
    def deserialize(
        cls,
        node: Node,
        serialized_data: typing.Mapping[str, typing.Any],
        restore_uuid: RestoreUuidOption = RestoreUuidOption.ATTEMPT_RESTORE,
        context: NodeDeserializationContext | None = None,
    ) -> UtilObject | None:
        """Create a util object from serialized data and add it to a node.

        Args:
            node (Node): node to add the object to.
            serialized_data (typing.Mapping[str, typing.Any]): serialized object.
            restore_uuid (RestoreUuidOption): how the serialized uuid is restored.
            context (NodeDeserializationContext | None): deserialization context.

        Returns:
            UtilObject | None: new object, None if its type isn't registered.
        """
        util_object_cls = NYX_REGISTRY.get_util_object_cls(
            serialized_data[cls.TYPE_ID_KEY]
        )
        if util_object_cls is None:
            return None

        uuid = cls.choose_new_uuid(
            stage=node.stage,
            serialized_data=serialized_data,
            restore_option=restore_uuid,
        )
        util_object = util_object_cls(uuid=uuid)
        util_object.apply_properties(serialized_data)
        node.add_util_object(util_object)
        if context is not None:
            context.register(
                serialized_uuid=serialized_data[cls.UUID_KEY], new_uuid=util_object.uuid
            )
        return util_object

    @classmethod
    def get_type_id(cls) -> str:
        """str: unique type id. Subclasses must implement."""
        raise NotImplementedError

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI. Subclasses must implement."""
        raise NotImplementedError


def get_configured_color(config_field: str, fallback: str) -> str:
    """Get a color from the graphics stage section of the config.

    Args:
        config_field (str): name of the config value, such as `default_note_color`.
        fallback (str): color to use when the configured value isn't a color.

    Returns:
        str: the configured color, or the fallback if it is invalid.
    """
    color = getattr(get_app_config().values.editor_widgets.graphics_stage, config_field)
    if QtGui.QColor(color).isValid():
        return color
    LOGGER.warning(f"Invalid {config_field} {color!r} in the config, using {fallback!r}")
    return fallback


def _as_point(value: QtCore.QPointF | typing.Iterable[float]) -> QtCore.QPointF:
    if isinstance(value, (QtCore.QPointF, QtCore.QPoint)):
        return QtCore.QPointF(value)
    return QtCore.QPointF(*value)


def _as_size(value: QtCore.QSizeF | typing.Iterable[float]) -> QtCore.QSizeF:
    if isinstance(value, (QtCore.QSizeF, QtCore.QSize)):
        return QtCore.QSizeF(value)
    return QtCore.QSizeF(*value)
