import copy
import logging
import pathlib
import typing
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
        return ":/icons/function"

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
        self._removed_components = False
        # Serialized value of each component of the source file, when it was loaded.
        self._source_values: dict[str, typing.Any] = {}

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

    def reload(self, overrides: dict[str, typing.Any] | None = None) -> None:
        """Load the contents of the source file again.

        Values set on this node are kept, links to its components are too as long as
        the component is still in the source file.

        Args:
            overrides (dict[str, typing.Any] | None): serialized values to set over
                the ones of the file, by component name. Defaults to the values changed
                on this node.
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
        if self._removed_components:
            self._removed_components = False
            self._clear_stage_history()

    def _clear_stage_history(self) -> None:
        """Forget the undo history of the stage, it holds commands on what was removed.

        Done once the running event is over: reloading also happens while a command
        is run or undone, and the stack can't be cleared from under it.
        """
        LOGGER.warning(f"{self.path}: components were removed, undo history cleared")
        stage_ref = weakref.ref(self.stage)

        def clear():
            stage = stage_ref()
            if stage is not None and shiboken6.isValid(stage):
                stage.clear_undo_history()

        QtCore.QTimer.singleShot(0, clear)

    def _load(self, overrides: dict[str, typing.Any]) -> None:
        """Replace the children and the components taken from the source file.

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
        """Create, update and remove the components taken from the source file.

        Args:
            components_data (list[dict]): serialized components of the source node.
            overrides (dict[str, typing.Any]): serialized values set on this node.
            context (NodeDeserializationContext): context of the source contents.
        """
        source_values = {}
        for component_data in components_data:
            name = component_data[NodeComponent.NAME_KEY]
            if name == self.SOURCE_COMPONENT_NAME:
                LOGGER.warning(
                    f"{self.path}: the source has a component named "
                    f"'{name}', it is left out"
                )
                continue

            existing = self._find_component(name)
            if existing is not None and existing.get_type_id() != component_data.get(
                NodeComponent.TYPE_ID_KEY
            ):
                self._drop_component(existing)
                existing = None

            # Same uuid for a component that stays, so links to it stay.
            data = copy.copy(component_data)
            if existing is not None:
                data[NodeComponent.UUID_KEY] = str(existing.uuid)
            component = NodeComponent.deserialize(
                data=data,
                node=self,
                context=context,
                component=existing,
                restore_uuid=(
                    RestoreUuidOption.RESTORE
                    if existing is not None
                    else RestoreUuidOption.GENERATE_NEW
                ),
            )
            context.register(
                serialized_uuid=component_data.get(NodeComponent.UUID_KEY),
                new_uuid=component.uuid,
            )
            source_values[name] = component_data.get("value")
            if existing is None:
                self.components_model.add_component(component)
            component.mark_as_built_in()

            if name in overrides:
                try:
                    component.restore_value(overrides[name], context)
                except Exception as err:
                    LOGGER.warning(f"{component.path}: dropped the value set: {err}")

        self._source_values = source_values
        for component in self.mirrored_components():
            if component.name not in source_values:
                LOGGER.warning(
                    f"{component.path} is not in the source anymore, it is removed"
                )
                self._drop_component(component)

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

    def _drop_component(self, component: NodeComponent) -> None:
        """Remove a component and the links to it.

        Args:
            component (NodeComponent): component to remove.
        """
        self._removed_components = True
        for link_uuid in list(component.links_uuids):
            if self.stage.uuid_map.get(link_uuid) is not None:
                self.stage.unregister_link(link_uuid)
        self.components_model.remove_component(component.uuid, force=True)

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
            for component in self.mirrored_components():
                component.mark_as_built_in()
            # Links to the new components, and the ones inside the source, need them.
            self.stage.register_node(self)
            overrides = self.collect_overrides()
        finally:
            self._loading = False
        self.reload(overrides=overrides)
