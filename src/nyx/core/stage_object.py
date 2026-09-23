import typing
import pathlib
import logging
from collections import OrderedDict

from uuid import UUID, uuid4

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
        self.stage.uuid_map.pop(self._uuid)
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
    def as_uuid(value: UUID | str | None) -> None:
        if isinstance(value, UUID):
            return value
        elif isinstance(value, str):
            return UUID(value)
        elif value is None:
            return uuid4()
        else:
            raise TypeError(f"Invalid UUID input: {value}")
