import typing
import copy
import dataclasses
from collections import OrderedDict, deque
from uuid import UUID

from ..stage_object import StageObject
from ..link import Link


if typing.TYPE_CHECKING:
    from ..node import Node
    from ..stage import Stage


@dataclasses.dataclass
class NodeSerializationContext:
    """Collects data shared while serializing nodes.

    Attributes:
        stage: stage being serialized
        entry_node: node serialization started from
    """

    stage: Stage
    entry_node: Node
    _links_uuids: set[UUID] = dataclasses.field(default_factory=set, init=False)

    def collect_links(self, from_node: Node):
        """Collect uuids of all links touching the node's components.

        Args:
            from_node (Node): node whose components are inspected.
        """
        for component in from_node.components_model.list_components():
            self._links_uuids.update(component.links_uuids)

    def get_serialized_links(self) -> list[OrderedDict]:
        """Serialize the collected links.

        Returns:
            list[OrderedDict]: serialized links.
        """
        return [
            self.stage.get_object(link_uuid).serialize()
            for link_uuid in deque(self._links_uuids)
        ]


@dataclasses.dataclass
class NodeDeserializationContext:
    """Tracks state shared while deserializing nodes.

    Attributes:
        stage: stage receiving the nodes
        entry_node: node deserialization started from
        defer_links: collect links instead of creating them, so the caller can
    """

    stage: Stage
    entry_node: Node | None = None
    defer_links: bool = False  # True: collect links, caller creates them

    _uuid_map: dict[UUID, UUID] = dataclasses.field(default_factory=dict, init=False)
    _raw_links: list[dict] = dataclasses.field(default_factory=list, init=False)

    def register(self, serialized_uuid: UUID | str | None, new_uuid: UUID) -> None:
        """Map a serialized uuid to the uuid of the object created for it.

        Args:
            serialized_uuid (UUID | str | None): uuid found in serialized data.
            new_uuid (UUID): uuid of the created object.
        """
        if serialized_uuid is not None:
            self._uuid_map[StageObject.as_uuid(serialized_uuid)] = new_uuid

    def resolve(self, serialized_uuid: UUID | str) -> UUID | None:
        """Look up the new uuid for a serialized uuid.

        Args:
            serialized_uuid (UUID | str): uuid found in serialized data.

        Returns:
            UUID | None: new uuid, None if not registered.
        """
        return self._uuid_map.get(StageObject.as_uuid(serialized_uuid))

    def collect_links(self, links_data: list[dict]) -> None:
        """Store serialized links to be created later.

        Args:
            links_data (list[dict]): serialized links.
        """
        self._raw_links.extend(links_data)

    def remap_link(self, link_data: dict) -> dict | None:
        """Copy of link_data with endpoints created in this run remapped.

        Endpoints not created in this run are kept as they are (they already
        live in the stage). Returns None if the link touches nothing we created.
        """
        src_raw = UUID(str(link_data[Link.SOURCE_UUID_KEY]))
        tgt_raw = UUID(str(link_data[Link.TARGET_UUID_KEY]))
        src = self._uuid_map.get(src_raw)
        tgt = self._uuid_map.get(tgt_raw)

        if src is None and tgt is None:
            return None

        remapped = copy.copy(link_data)
        remapped[Link.SOURCE_UUID_KEY] = str(src if src is not None else src_raw)
        remapped[Link.TARGET_UUID_KEY] = str(tgt if tgt is not None else tgt_raw)
        return remapped

    def resolved_links(self) -> list[tuple[UUID, UUID]]:
        """Unique (source, target) pairs for all collected links."""
        pairs: list[tuple[UUID, UUID]] = []
        for data in self._raw_links:
            target_raw = StageObject.as_uuid(data[Link.TARGET_UUID_KEY])
            target_uuid = self._uuid_map.get(target_raw)
            if target_uuid is None:
                continue  # target is outside the paste - don't touch it

            source_raw = StageObject.as_uuid(data[Link.SOURCE_UUID_KEY])
            source_uuid = self._uuid_map.get(
                source_raw, source_raw
            )  # external source - keep it

            uuid_pair = (source_uuid, target_uuid)
            if uuid_pair not in pairs:
                pairs.append(uuid_pair)
        return pairs
