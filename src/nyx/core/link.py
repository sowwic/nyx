import logging
import typing
import pathlib
from uuid import UUID
from collections import OrderedDict

from .stage_object import StageObject
from .path_resolver import StagePathResolver
from .exceptions import StageObjectQueryError
from ..static.enums import RestoreUuidOption

if typing.TYPE_CHECKING:
    from .stage import Stage
    from .node import Node
    from .node_component import NodeComponent

LOGGER = logging.getLogger(__name__)


type LinkLike = Link | UUID | str


class Link(StageObject):
    SOURCE_UUID_KEY = "source_uuid"
    TARGET_UUID_KEY = "target_uuid"

    def __init__(
        self,
        stage: Stage,
        source: UUID | str,
        target: UUID | str,
        uuid: UUID | str | None = None,
    ):
        self._stage = stage
        self.source = self.as_uuid(source)
        self.target = self.as_uuid(target)
        super().__init__(uuid)

    def __repr__(self) -> str:
        return f"({self.__class__.__name__}): {self.path_connection_str}"

    @property
    def stage(self) -> Stage:
        return self._stage

    @property
    def source_component(self) -> NodeComponent:
        return self.stage.get_object(self.source)

    @property
    def source_path(self) -> pathlib.PurePosixPath:
        return self.source_component.path

    @property
    def source_node(self) -> Node:
        return self.source_component.node

    @property
    def target_component(self) -> NodeComponent:
        return self.stage.get_object(self.target)

    @property
    def target_path(self) -> pathlib.PurePosixPath:
        return self.target_component.path

    @property
    def target_node(self) -> Node:
        return self.target_component.node

    @property
    def path_connection_str(self) -> str:
        if not self.is_valid:
            return "INVALID"
        return f"{self.source_path} -> {self.target_path}"

    @property
    def is_valid(self) -> bool:
        try:
            self.source_component
        except StageObjectQueryError:
            return False
        try:
            self.target_component
        except StageObjectQueryError:
            return False
        return True

    @classmethod
    def is_registered(cls, stage: Stage, link: LinkLike) -> bool:
        try:
            link: Link = stage.get_object(link)
        except StageObjectQueryError:
            return False

        if not link.is_valid:
            return False

        present_in_source = link.uuid in link.source_component.links_uuids
        present_in_target = link.uuid in link.target_component.links_uuids

        return all([present_in_source, present_in_target])

    def serialize(self) -> OrderedDict[str, typing.Any]:
        serialized_data = super().serialize()
        serialized_data[self.META_DATA_KEY].update(
            {
                "relative_path": StagePathResolver.compute_relative_path(
                    source_path=self.source_path, destination_path=self.target_path
                ).as_posix()
            }
        )
        serialized_data[self.SOURCE_UUID_KEY] = str(self.source)
        serialized_data[self.TARGET_UUID_KEY] = str(self.target)
        return serialized_data

    @classmethod
    def deserialize(
        cls,
        stage: Stage,
        serialized_link: OrderedDict[str, typing.Any],
        link: Link | None = None,
        restore_uuid: RestoreUuidOption = RestoreUuidOption.ATTEMPT_RESTORE,
    ):
        new_uuid = cls.choose_new_uuid(
            stage=stage,
            serialized_data=serialized_link,
            restore_option=restore_uuid,
        )
        if not link:
            link = cls(
                stage=stage,
                source=serialized_link[cls.SOURCE_UUID_KEY],
                target=serialized_link[cls.TARGET_UUID_KEY],
                uuid=new_uuid,
            )
        else:
            link.uuid = new_uuid

        return link
