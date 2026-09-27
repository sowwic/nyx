import typing
import pathlib
import logging
from collections import OrderedDict

from uuid import UUID, uuid4

from ..static.enums import RestoreUuidOption

if typing.TYPE_CHECKING:
    from .stage import Stage


LOGGER = logging.getLogger(__name__)


class StageObject:
    REQUIRED_PLUGINS = set()

    UUID_KEY = "uuid"
    META_DATA_KEY: str = "metadata"
    REQUIRED_PLUGINS_KEY: str = "required_plugins"
    NYX_VERSION_METADATA_KEY: str = "nyx_version"

    def __init__(self, uuid: UUID | str | None = None):
        self._uuid = self.as_uuid(uuid)

    @property
    def stage(self) -> Stage:
        raise NotImplementedError("StageObject subclass must implement stage property.")

    @property
    def uuid(self) -> UUID:
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
        raise NotImplementedError("StageObject subclass must implement path property")

    @property
    def metadata(self) -> dict[str, typing.Any]:
        return {}

    def serialize(self) -> OrderedDict[str, typing.Any]:
        serialized_data = OrderedDict()
        serialized_data[self.UUID_KEY] = str(self.uuid)
        serialized_data[self.META_DATA_KEY] = self.metadata
        if self.REQUIRED_PLUGINS:
            serialized_data[self.REQUIRED_PLUGINS_KEY] = list(self.REQUIRED_PLUGINS)

        return serialized_data

    @classmethod
    def deserialize(
        cls,
    ) -> StageObject:
        raise NotImplementedError(
            "StageObject subclass must implement deserialize() method"
        )

    @staticmethod
    def as_uuid(value: StageObject | UUID | str | None, strict: bool = False) -> UUID:
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
        if restore_option is RestoreUuidOption.GENERATE_NEW:
            return uuid4()

        serialized_uuid = cls.as_uuid(serialized_data[cls.UUID_KEY])

        if restore_option is RestoreUuidOption.RESTORE:
            return serialized_uuid
        elif restore_option is RestoreUuidOption.ATTEMPT_RESTORE:
            if stage is None:
                return serialized_uuid
            return serialized_uuid if serialized_uuid not in stage.uuid_map else uuid4()
