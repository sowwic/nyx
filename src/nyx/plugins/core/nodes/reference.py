import copy
import logging
import pathlib
import typing
import uuid
from uuid import UUID
import weakref
from collections import OrderedDict

import shiboken6
from PySide6 import QtCore
from nyx.api.v1 import (
    Node,
    NodeComponent,
    NodeDeserializationContext,
    NodeSerializationContext,
    CoreNodes,
    CoreNodeComponents,
    NodeFlag,
    RestoreUuidOption,
    static_vars,
)
from nyx.utils import file_fn

LOGGER = logging.getLogger(__name__)


class ReferenceSourceError(Exception):
    """The source of a reference node can't be loaded."""


class ReferenceNode(Node):
    """Node standing for the top node of a stage file.

    The components of the top node of the source file are the ones of the reference
    node: they can be given values and linked to, but not added, removed, renamed or
    given another datatype. The nodes inside the source file are loaded as children,
    locked and never stored with the stage. They are loaded again whenever the stage
    is opened, so changes made to the source file show up.
    """

    DEFAULT_NAME = "reference"

    SOURCE_COMPONENT_NAME = "source"
    SOURCE_KEY = "source"
    SOURCE_VALUES_KEY = "source_values"
    SOURCE_UUIDS_KEY = "source_uuids"

    @classmethod
    def get_type_id(cls) -> str:
        """str: node type id."""
        return CoreNodes.REFERENCE

    @classmethod
    def get_type_flags(cls) -> NodeFlag:
        """NodeFlag: the inner nodes and the components are owned by the source."""
        return (
            super().get_type_flags() | NodeFlag.LOCKS_CHILDREN | NodeFlag.LOCKS_STRUCTURE
        )

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return "Reference"

    @classmethod
    def get_type_icon(cls) -> str:
        """str: resource path of the type icon."""
        return ":/icons/asterisk"

    @classmethod
    def get_description(cls) -> str:
        """str: what the node type does, shown in the palette."""
        return "Stands for a stage file, with the components of its top node."

    @classmethod
    def get_tags(cls) -> set[str]:
        """set[str]: node tags."""
        return {"common", "stage"}

    def setup(self):
        """Add the source component."""
        self._loading = False
        self._loaded_source: str | None = None
        self._load_error = "No source set"
        # Serialized value of each component of the source file, when it was loaded.
        self._source_values: dict[str, typing.Any] = {}
        # Uuid in the source file of the component each component stands for, by name.
        # A component renamed in the source is found again by it.
        self._source_uuids: dict[str, str] = {}

        self.source_cpnt = self.components_model.create_component(
            CoreNodeComponents.FILE
        )
        self.source_cpnt.name = self.SOURCE_COMPONENT_NAME
        self.source_cpnt.description = (
            "Stage file to reference, absolute or relative to the file of this stage."
        )
        self.components_model.add_component(self.source_cpnt)

        self.bind_subtitle_to_component(
            self.SOURCE_COMPONENT_NAME, lambda component: self._compose_subtitle()
        )

    @property
    def source(self) -> str:
        """str: source as it was set, empty for none."""
        return str(self.source_cpnt.raw_value or "").strip()

    @property
    def load_error(self) -> str:
        """str: why the source couldn't be loaded, empty if it was."""
        return self._load_error

    def _compose_subtitle(self) -> str:
        """Get the text shown next to the name.

        Returns:
            str: the reason the source isn't loaded, otherwise the source file name.
        """
        return self._load_error or pathlib.PurePath(self.source).name

    def mirrored_components(self) -> list[NodeComponent]:
        """List the components taken from the source file.

        Returns:
            list[NodeComponent]: all components but the source.
        """
        return [
            component
            for component in self.components_model.list_components()
            if component is not self.source_cpnt
        ]

    # ======== Source ========= #

    def _owning_reference(self) -> ReferenceNode | None:
        """Get the closest reference node containing this one.

        Returns:
            ReferenceNode | None: the reference node, None for a node in the stage.
        """
        parent = self.parent()
        while parent is not None:
            if isinstance(parent, ReferenceNode):
                return parent
            parent = parent.parent()
        return None

    def resolve_source_path(self) -> pathlib.Path | None:
        """Get the file the source points at.

        A relative source is relative to the folder of the stage file, or of the source
        file of the reference node this one is loaded by.

        Returns:
            pathlib.Path | None: the file path, None if there is no source or the
                relative source has nothing to be relative to.
        """
        if not self.source:
            return None

        path = pathlib.Path(self.source)
        if path.is_absolute():
            return path

        owner = self._owning_reference()
        if owner is not None:
            owner_path = owner.resolve_source_path()
            return owner_path.parent / path if owner_path else None
        if self.stage.file_path is None:
            return None
        return pathlib.Path(self.stage.file_path).parent / path

    def _containing_files(self) -> set[pathlib.Path]:
        """Get the files this node is loaded from, directly or through other nodes.

        Returns:
            set[pathlib.Path]: resolved file paths.
        """
        files = set()
        if self.stage.file_path is not None:
            files.add(pathlib.Path(self.stage.file_path).resolve())
        owner = self._owning_reference()
        while owner is not None:
            owner_path = owner.resolve_source_path()
            if owner_path is not None:
                files.add(owner_path.resolve())
            owner = owner._owning_reference()
        return files

    def _read_source(self) -> OrderedDict:
        """Read the serialized top node of the source file.

        Returns:
            OrderedDict: serialized node.

        Raises:
            ReferenceSourceError: if the file can't be used.
        """
        if not self.source:
            raise ReferenceSourceError("No source set")

        path = self.resolve_source_path()
        if path is None:
            raise ReferenceSourceError("Save the stage to use a relative source")
        if path.suffix != static_vars.NYX_FILE_EXTENSION:
            raise ReferenceSourceError(f"Not a {static_vars.NYX_FILE_EXTENSION} file")
        if not path.is_file():
            raise ReferenceSourceError(f"File doesn't exist: {path}")
        if path.resolve() in self._containing_files():
            raise ReferenceSourceError("A stage can't reference itself")

        try:
            return file_fn.load_json(path, object_pairs_hook=OrderedDict)
        except Exception as err:
            raise ReferenceSourceError(f"Can't read the file: {err}") from err

    # ======== Loading ========= #

    def on_component_edited(self, component: NodeComponent) -> None:
        """Load the new source when it is edited.

        Args:
            component (NodeComponent): component that changed.
        """
        if self._loading or component is not self.source_cpnt:
            return
        if self.source != self._loaded_source:
            # A different file has its own values.
            self.reload(overrides={})

    def collect_overrides(self) -> dict[str, typing.Any]:
        """Get the values that were changed on this node.

        Returns:
            dict[str, typing.Any]: serialized value by component name, for the
                components whose value isn't the one of the source file.
        """
        return {
            component.name: component.serialize_value()
            for component in self.mirrored_components()
            if component.name in self._source_values
            and component.serialize_value() != self._source_values[component.name]
        }

    def get_source_file(self) -> pathlib.Path | None:
        """pathlib.Path | None: file the source points at."""
        return self.resolve_source_path()

    def reload_source(self) -> None:
        """Load the source file again."""
        self.reload()

    def reload(
        self,
        overrides: dict[str, typing.Any] | None = None,
        clear_history: bool = True,
    ) -> None:
        """Load the contents of the source file again.

        Values set on this node are kept. So are its components and the links to them,
        the ones that are not in the source anymore are marked as invalid.

        Args:
            overrides (dict[str, typing.Any] | None): serialized values to set over
                the ones of the file, by component name. Defaults to the values changed
                on this node.
            clear_history (bool): forget the undo history of the stage: a reload isn't
                something it can undo. Not for the load that comes with creating the
                node, which the history has to be able to undo and redo.
        """
        if self._loading:
            return
        if overrides is None:
            overrides = self.collect_overrides()

        self._loading = True
        try:
            self._load(overrides)
        finally:
            self._loading = False
            self.emitDataChanged()
        if clear_history:
            self._clear_stage_history()

    def _clear_stage_history(self) -> None:
        """Forget the undo history of the stage, it holds commands from before the load.

        Done once the running event is over: reloading also happens while a command
        is run or undone, and the stack can't be cleared from under it.
        """
        LOGGER.info(f"{self.path}: reloaded, undo history cleared")
        stage_ref = weakref.ref(self.stage)

        def clear():
            stage = stage_ref()
            if stage is not None and shiboken6.isValid(stage):
                stage.clear_undo_history()

        QtCore.QTimer.singleShot(0, clear)

    def _load(self, overrides: dict[str, typing.Any]) -> None:
        """Replace the children and update the components taken from the source file.

        Args:
            overrides (dict[str, typing.Any]): serialized values set on this node.
        """
        self._remove_children()
        self._loaded_source = self.source
        self._load_error = ""
        try:
            data = self._read_source()
        except ReferenceSourceError as err:
            self._load_error = str(err)
            if self.source:
                LOGGER.error(f"{self.path}: {err}")
            # Nothing is known of the source: the components stay, and so do the links.
            for component in self.mirrored_components():
                component.set_invalid_reason(self._load_error)
            return

        context = NodeDeserializationContext(
            stage=self.stage, entry_node=self, defer_links=True
        )
        for child_data in data.get(self.CHILDREN_KEY, []):
            Node.deserialize(
                serialized_node=child_data,
                parent_node=self,
                context=context,
                restore_uuid=RestoreUuidOption.GENERATE_NEW,
            )
        self._load_components(data.get(self.COMPONENTS_KEY, []), overrides, context)

        try:
            self.deserialize_links(
                links_data=data.get(self.LINKS_KEY, []),
                restore_uuid=RestoreUuidOption.GENERATE_NEW,
                context=context,
            )
            context.run_deferred()
        except Exception:
            LOGGER.exception(f"{self.path}: can't restore the links of the source")

    def _load_components(
        self,
        components_data: list[dict],
        overrides: dict[str, typing.Any],
        context: NodeDeserializationContext,
    ) -> None:
        """Create and update the components taken from the source file.

        A component that is not in the source anymore stays, marked as invalid, and so
        do its links: they are left for the user to remove.

        Args:
            components_data (list[dict]): serialized components of the source node.
            overrides (dict[str, typing.Any]): serialized values set on this node.
            context (NodeDeserializationContext): context of the source contents.
        """
        source_values = {}
        source_uuids = {}
        matched: set[UUID] = set()
        for component_data in components_data:
            name = component_data[NodeComponent.NAME_KEY]
            if name == self.SOURCE_COMPONENT_NAME:
                LOGGER.warning(
                    f"{self.path}: the source has a component named "
                    f"'{name}', it is left out"
                )
                continue

            source_uuid = str(component_data.get(NodeComponent.UUID_KEY))
            existing = self._find_existing_component(name, source_uuid, matched)
            if existing is not None:
                matched.add(existing.uuid)
                if existing.get_type_id() != component_data.get(
                    NodeComponent.TYPE_ID_KEY
                ):
                    # Can't turn into the new type. It goes once the user removes it.
                    existing.set_invalid_reason("Changed type in the source")
                    LOGGER.warning(f"{existing.path} changed type in the source")
                    continue

            # What was set on the component, under the name it has now.
            override_key = existing.name if existing is not None else name

            # The same uuid for a component that stays, so links to it stay. A new one
            # gets a uuid worked out from the node, so it is the same whenever the node
            # is created again, like when a paste is undone and redone.
            data = copy.copy(component_data)
            data[NodeComponent.UUID_KEY] = str(
                existing.uuid if existing is not None else self._derive_uuid(name)
            )
            if existing is not None and name != existing.name:
                if self._find_component(name) is None:
                    LOGGER.info(f"{existing.path} was renamed to '{name}'")
                else:
                    data[NodeComponent.NAME_KEY] = existing.name
            component = NodeComponent.deserialize(
                data=data,
                node=self,
                context=context,
                component=existing,
                restore_uuid=RestoreUuidOption.RESTORE,
            )
            context.register(
                serialized_uuid=component_data.get(NodeComponent.UUID_KEY),
                new_uuid=component.uuid,
            )
            source_values[component.name] = component_data.get("value")
            source_uuids[component.name] = source_uuid
            matched.add(component.uuid)
            if existing is None:
                self.components_model.add_component(component)
            component.mark_as_built_in()
            component.set_invalid_reason("")

            if override_key in overrides:
                try:
                    component.restore_value(overrides[override_key], context)
                except Exception as err:
                    LOGGER.warning(f"{component.path}: dropped the value set: {err}")

        self._source_values = source_values
        self._source_uuids = source_uuids
        for component in self.mirrored_components():
            if component.uuid not in matched:
                component.set_invalid_reason("Not in the source anymore")
                LOGGER.warning(f"{component.path} is not in the source anymore")

    def _derive_uuid(self, name: str) -> UUID:
        """Work out the uuid of a component from the uuid of this node and its name.

        Args:
            name (str): name of the component.

        Returns:
            UUID: the same uuid for the same node and name. It has the bits of a random
                uuid, since stage objects are looked up from the text of their uuid
                as one.
        """
        return uuid.UUID(bytes=uuid.uuid5(self.uuid, name).bytes, version=4)

    def _find_existing_component(
        self, name: str, source_uuid: str, taken: set[UUID]
    ) -> NodeComponent | None:
        """Find the component of this node standing for a component of the source.

        The component of the same source component is the one, even if it was renamed.
        Otherwise it is the one with the same name.

        Args:
            name (str): name of the component in the source.
            source_uuid (str): uuid of the component in the source file.
            taken (set[UUID]): uuids of the components already used.

        Returns:
            NodeComponent | None: the component, None if the source one is new.
        """
        for component in self.mirrored_components():
            if (
                component.uuid not in taken
                and self._source_uuids.get(component.name) == source_uuid
            ):
                return component

        component = self._find_component(name)
        if component is None or component is self.source_cpnt or component.uuid in taken:
            return None
        return component

    def _find_component(self, name: str) -> NodeComponent | None:
        """Get a component by name.

        Args:
            name (str): component name.

        Returns:
            NodeComponent | None: the component, None if there is none.
        """
        try:
            return self.components_model.get_component(name)
        except ValueError:
            return None

    def _remove_children(self) -> None:
        """Remove the nodes loaded from the source file and the links between them."""
        children = self.list_children()
        for node in [*children, *self.list_children_tree()]:
            for component in node.components_model.list_components():
                for link_uuid in list(component.links_uuids):
                    if self.stage.uuid_map.get(link_uuid) is not None:
                        self.stage.unregister_link(link_uuid)
        if children:
            self.stage.delete_node(children, ignore_lock=True)

    # ======== Serialization ========= #

    def serialize_contents(
        self, context: NodeSerializationContext
    ) -> OrderedDict[str, typing.Any]:
        """Serialize the components, without the children: the source has them.

        The components are kept so the node still has them if the source is gone.

        Args:
            context (NodeSerializationContext): serialization context.

        Returns:
            OrderedDict[str, typing.Any]: data merged into the serialized node.
        """
        contents = OrderedDict(self.components_model.serialize())
        contents[self.SOURCE_VALUES_KEY] = dict(self._source_values)
        contents[self.SOURCE_UUIDS_KEY] = dict(self._source_uuids)
        return contents

    def collect_serialized_links(self, context: NodeSerializationContext) -> None:
        """Store the links to the outside, the source brings back the inner ones.

        Args:
            context (NodeSerializationContext): serialization context.
        """
        inside = {self, *self.list_children_tree()}
        for component in self.components_model.list_components():
            for link_uuid in component.links_uuids:
                link = self.stage.get_object(link_uuid)
                other = (
                    link.target_component
                    if link.source_component is component
                    else link.source_component
                )
                if other.node not in inside:
                    context.collect_link_uuids([link_uuid])

    def deserialize_contents(
        self,
        serialized_node: OrderedDict[str, typing.Any],
        context: NodeDeserializationContext,
        restore_uuid: RestoreUuidOption,
    ) -> None:
        """Restore the components, then load the source file.

        Args:
            serialized_node (OrderedDict[str, typing.Any]): serialized node.
            context (NodeDeserializationContext): deserialization context.
            restore_uuid (RestoreUuidOption): how serialized uuids are restored.
        """
        self._loading = True
        try:
            self.components_model.deserialize(
                serialized_node.get(self.COMPONENTS_KEY, []),
                context=context,
                restore_uuid=restore_uuid,
            )
            if isinstance(serialized_node.get(self.SOURCE_KEY), str):
                self.source_cpnt.push_value(serialized_node[self.SOURCE_KEY])
            self._source_values = dict(serialized_node.get(self.SOURCE_VALUES_KEY, {}))
            self._source_uuids = dict(serialized_node.get(self.SOURCE_UUIDS_KEY, {}))
            for component in self.mirrored_components():
                component.mark_as_built_in()
            # Links to the new components, and the ones inside the source, need them.
            self.stage.register_node(self)
            overrides = self.collect_overrides()
        finally:
            self._loading = False
        # Creating the node is something the history undoes and redoes: keep it.
        self.reload(overrides=overrides, clear_history=False)
