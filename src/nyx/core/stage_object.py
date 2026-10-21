import typing
import pathlib
import logging
from collections import OrderedDict
from uuid import UUID, uuid4

from PySide6 import QtCore

from ..static.enums import RestoreUuidOption

if typing.TYPE_CHECKING:
    from .plugin_subsystem.registry import NyxPluginRegistryEntry
    from .stage import Stage


LOGGER = logging.getLogger(__name__)


class StageObject:
    """Base class for stage objects registered by uuid (nodes, components, links)."""

    UUID_KEY = "uuid"
    META_DATA_KEY: str = "metadata"
    SOURCE_PLUGIN_KEY: str = "source_plugin"
    NYX_VERSION_METADATA_KEY: str = "nyx_version"

    SOURCE_PLUGIN: NyxPluginRegistryEntry | None = None

    def __init__(self, uuid: UUID | str | None = None):
        """Initialize StageObject.

        Args:
            uuid (UUID | str | None): object uuid. Generated if omitted.
        """
        self._uuid = self.as_uuid(uuid)

    @property
    def stage(self) -> Stage:
        """Stage: owning stage. Subclasses must implement."""
        raise NotImplementedError("StageObject subclass must implement stage property.")

    @property
    def uuid(self) -> UUID:
        """UUID: unique id of the object. Setting it updates the stage uuid map."""
        return self._uuid

    @uuid.setter
    def uuid(self, value: UUID | str):
        value = value if isinstance(value, UUID) else UUID(value)
        if self._uuid == value:
            return

        LOGGER.debug(
            "Updating %s UUID: %s -> %s",
            self.__class__.__name__,
            str(self._uuid),
            str(value),
        )
        self.stage.uuid_map.pop(self._uuid, None)
        self._uuid = value
        self.stage.uuid_map[self._uuid] = self

    @property
    def path(self) -> pathlib.PosixPath:
        """pathlib.PosixPath: path in the stage. Subclasses must implement."""
        raise NotImplementedError("StageObject subclass must implement path property")

    @property
    def metadata(self) -> dict[str, typing.Any]:
        """dict[str, typing.Any]: extra data stored when serializing."""
        return {}

    def serialize(self) -> OrderedDict[str, typing.Any]:
        """Serialize the object.

        Returns:
            OrderedDict[str, typing.Any]: data with uuid, metadata and source plugin.
        """
        serialized_data = OrderedDict()
        serialized_data[self.UUID_KEY] = str(self.uuid)
        serialized_data[self.META_DATA_KEY] = self.metadata
        if self.SOURCE_PLUGIN is not None:
            serialized_data[self.SOURCE_PLUGIN_KEY] = (
                self.SOURCE_PLUGIN.plugin_cls.get_type_id()
            )

        return serialized_data

    @classmethod
    def deserialize(
        cls,
    ) -> StageObject:
        """Create an object from serialized data. Subclasses must implement.

        Returns:
            StageObject: deserialized object.
        """
        raise NotImplementedError(
            "StageObject subclass must implement deserialize() method"
        )

    @classmethod
    def resolve_qml_source(cls, component_path: str) -> QtCore.QUrl:
        """Resolve a QML file of the plugin that provides this type.

        Args:
            component_path (str): path relative to the plugin QML directory.

        Returns:
            QtCore.QUrl | None: file url, None if the type has no source plugin.

        Raises:
            ValueError: if the file doesn't exist.
        """
        if not cls.SOURCE_PLUGIN:
            return None

        path = cls.SOURCE_PLUGIN.plugin_cls.qml_directory() / component_path
        if not path.is_file():
            raise ValueError(f"Invalid QML source file: {path}")

        return QtCore.QUrl.fromLocalFile(str(path))

    @staticmethod
    def as_uuid(value: StageObject | UUID | str | None, strict: bool = False) -> UUID:
        """Convert a value to a uuid.

        Args:
            value (StageObject | UUID | str | None): object, uuid or uuid string.
            strict (bool): raise on None instead of generating a new uuid.

        Returns:
            UUID: converted uuid.

        Raises:
            ValueError: if value is None and strict is set.
            TypeError: if value is of an unsupported type.
        """
        if isinstance(value, StageObject):
            return value.uuid
        if isinstance(value, UUID):
            return value
        elif isinstance(value, str):
            return UUID(value)
        elif value is None:
            if not strict:
                return uuid4()
            raise ValueError(f"UUID must be of type UUID | str, got {value}")
        else:
            raise TypeError(f"Invalid UUID input: {value}")

    @classmethod
    def choose_new_uuid(
        cls,
        stage: Stage | None,
        serialized_data: OrderedDict[str, typing.Any],
        restore_option: RestoreUuidOption,
    ) -> UUID:
        """Pick the uuid for a deserialized object.

        Args:
            stage (Stage | None): stage used to detect uuid collisions.
            serialized_data (OrderedDict[str, typing.Any]): serialized object.
            restore_option (RestoreUuidOption): uuid restore strategy.

        Returns:
            UUID: uuid to use.
        """
        if restore_option is RestoreUuidOption.GENERATE_NEW:
            return uuid4()

        serialized_uuid = cls.as_uuid(serialized_data[cls.UUID_KEY])

        if restore_option is RestoreUuidOption.RESTORE:
            return serialized_uuid
        elif restore_option is RestoreUuidOption.ATTEMPT_RESTORE:
            if stage is None:
                return serialized_uuid

            return serialized_uuid if serialized_uuid not in stage.uuid_map else uuid4()

    @classmethod
    def get_type_icon(cls) -> str:
        """str: resource path of the type icon."""
        return ":/icons/stage_object"

    @classmethod
    def get_description(cls) -> str:
        """str: short text telling what the type does, empty for none."""
        return ""
