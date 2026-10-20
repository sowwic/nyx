import logging
import pathlib
import typing
from uuid import UUID

from nyx.api.v1 import (
    CoreDatatypes,
    CoreNodeComponents,
    Node,
    NodeComponent,
    NodeComponentFlag,
    NodeComponentValueMask,
    exceptions,
)
from nyx.core.path_resolver import StagePathResolver

if typing.TYPE_CHECKING:
    from nyx.core.contexts.serialization import NodeDeserializationContext
    from nyx.core.stage import Stage

LOGGER = logging.getLogger(__name__)


class StageReferenceComponent(NodeComponent):
    """Component pointing at a node or a component of the stage by path.

    A path with a suffix, like `/stage/node.component`, is the path of a component and
    any other path is the path of a node. The path can be absolute, or relative to the
    scope of the owning node.

    The target is remembered by uuid, so renaming or moving it doesn't break the
    reference, and pasting or importing a group re-points the copies at each other.
    The text value is the path the user gave. It finds the target when the uuid can't,
    for example when the group is imported into another stage.

    Only another reference can be linked into it, not a plain value.
    """

    DEFAULT_NAME = "reference"
    EDITOR_QML = "StageReferenceComponentItem"

    # What the reference may point at. Set on an instance to narrow it down, for example
    # to `(NodeComponent,)` when a node path makes no sense.
    target_types: tuple[type, ...] = (Node, NodeComponent)
    TARGET_UUID_KEY = "target_uuid"
    TARGET_PATH_KEY = "path"

    # Not set in `__init__`: the base class pushes its default value before that.
    _target_uuid: UUID | None = None

    @classmethod
    def get_type_id(cls) -> str:
        """str: component type id."""
        return CoreNodeComponents.STAGE_REFERENCE

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return "Stage Reference"

    @classmethod
    def get_type_icon(cls) -> str:
        """str: resource path of the type icon."""
        return ":/icons/stage_reference"

    @classmethod
    def get_tags(cls) -> set[str]:
        """set[str]: component tags."""
        return {"common", "value"}

    @classmethod
    def get_type_default_flags(cls) -> NodeComponentFlag:
        """NodeComponentFlag: flags set on new components of the type."""
        return NodeComponentFlag.STATIC | NodeComponentFlag.EDITABLE

    @classmethod
    def get_default_expanded_state(cls) -> bool:
        """bool: reference components start expanded."""
        return True

    @classmethod
    def get_type_default_datatype(cls) -> str:
        """str: references have a datatype of their own."""
        return CoreDatatypes.REFERENCE

    # ======== Resolving ========= #

    def _owner_stage(self) -> Stage | None:
        """Stage: stage of the owning node, None while the component is detached."""
        model = self.model()
        node = model.node if model is not None else None
        return node.stage if node is not None else None

    def _find_target_by_text(self, text: typing.Any) -> Node | NodeComponent | None:
        """Find the target by a path, absolute or relative to the scope of the owner.

        Args:
            text (typing.Any): path text.

        Returns:
            Node | NodeComponent | None: node for a node path, component for a
                path with a suffix. None if the text isn't the path of either.
        """
        stage = self._owner_stage()
        if stage is None or not isinstance(text, str) or not text.strip():
            return None

        path = pathlib.PurePosixPath(text.strip())
        if StagePathResolver.is_relative_path(path):
            path = StagePathResolver.compute_absolute_path(self.node.scope, path)
        try:
            # The suffix decides: a component path gives a component, else a node.
            target = stage.get_object(path)
        except (exceptions.StageObjectQueryError, ValueError):
            return None
        return target if isinstance(target, self.target_types) else None

    @property
    def target_uuid(self) -> UUID | None:
        """UUID | None: uuid the reference points at, None if it has no target yet."""
        return self._target_uuid

    @property
    def target(self) -> Node | NodeComponent | None:
        """Node | NodeComponent | None: what the reference points at, None if not found.

        The uuid is tried first and the text only if it fails. The uuid is kept even
        when the object is missing, so a target restored later is found again.
        """
        stage = self._owner_stage()
        if stage is None:
            return None

        if self._target_uuid is not None:
            target = stage.uuid_map.get(self._target_uuid)
            if isinstance(target, self.target_types):
                return target

        target = self._find_target_by_text(self.raw_value)
        if target is not None:
            self._target_uuid = target.uuid
        return target

    def resolve_target(self) -> Node | NodeComponent:
        """Get the node or component the reference points at.

        An input link replaces the target: the path it provides is used.

        Returns:
            Node | NodeComponent: target.

        Raises:
            StageObjectQueryError: if there is nothing at the path.
        """
        if self.input_links:
            target = self._find_target_by_text(super().pull_value())
        else:
            target = self.target
        if target is None:
            raise exceptions.StageObjectQueryError(
                f"{self.name}: nothing found for reference {self.raw_value!r}"
            )
        return target

    @property
    def target_node(self) -> Node | None:
        """Node | None: the node, or the node owning the component, None if not found."""
        target = self.target
        if isinstance(target, NodeComponent):
            return target.node
        return target

    @property
    def target_component(self) -> NodeComponent | None:
        """NodeComponent | None: the component, None for a node path or no target."""
        target = self.target
        return target if isinstance(target, NodeComponent) else None

    def resolve_node(self) -> Node:
        """Get the node the reference points at.

        Returns:
            Node: target node.

        Raises:
            StageObjectQueryError: if the path isn't the path of an existing node.
        """
        target = self.resolve_target()
        if not isinstance(target, Node):
            raise exceptions.StageObjectQueryError(
                f"{self.name}: {target.path} is a component, not a node"
            )
        return target

    def resolve_component(self) -> NodeComponent:
        """Get the component the reference points at.

        Returns:
            NodeComponent: target component.

        Raises:
            StageObjectQueryError: if the path isn't the path of an existing component.
        """
        target = self.resolve_target()
        if not isinstance(target, NodeComponent):
            raise exceptions.StageObjectQueryError(
                f"{self.name}: {target.path} is a node, not a component"
            )
        return target

    @property
    def is_valid(self) -> bool:
        """bool: the reference points at an existing node or component."""
        try:
            self.resolve_target()
        except exceptions.StageObjectQueryError:
            return False
        return True

    def current_path_text(self) -> str:
        """Get the text the reference stands for right now.

        Returns:
            str: absolute path of the target, the given text if there is no target.
        """
        target = self.target
        if target is not None:
            return target.path.as_posix()
        return "" if self.raw_value is None else str(self.raw_value)

    def current_display_text(self) -> str:
        """Get the text shown for the reference right now.

        Returns:
            str: the target as a string, like `LogNode (/stage/log)`. The given text
                if there is no target.
        """
        target = self.target
        if target is not None:
            return str(target)
        return "" if self.raw_value is None else str(self.raw_value)

    # ======== Values ========= #

    def push_value(self, value: typing.Any, evaluate: bool = True):
        """Set the text of the reference and look for its target.

        Args:
            value (typing.Any): path of the target, absolute or relative to the scope
                of the owner.
            evaluate (bool): unused, a path is never evaluated.
        """
        # Forget the old target first: setting the value tells the views, and they
        # ask for the display value right away.
        self._target_uuid = None
        super().push_value(value, evaluate=False)
        self._refresh_cached_values()

    def _refresh_cached_values(self) -> None:
        """Make the cached and display values match the target, and tell the views."""
        self.setData(self.current_path_text(), role=self.Roles.CACHED_VALUE)
        self.setData(self.current_display_text(), role=self.Roles.DISPLAY_VALUE)
        # Display value and validity are worked out on request, not stored: no
        # `setData` reports them, and the target may have changed without the text.
        model = self.model()
        if model is not None:
            model.dataChanged.emit(
                self.index(),
                self.index(),
                [
                    self.Roles.CACHED_VALUE,
                    self.Roles.DISPLAY_VALUE,
                    self.Roles.IS_VALID,
                ],
            )

    def pull_value(
        self, value_mask: NodeComponentValueMask = NodeComponentValueMask.CACHE
    ) -> typing.Any:
        """Get the path of the target, which follows renames.

        Args:
            value_mask (NodeComponentValueMask): which value to get.

        Returns:
            typing.Any: path of the target, the raw text for the raw mask.
        """
        if self.input_links or value_mask is NodeComponentValueMask.RAW:
            return super().pull_value(value_mask)
        return self.current_path_text()

    def get_display_value(self) -> str:
        """str: the target as a string, the given text if it can't be found."""
        if self.input_links:
            return super().get_display_value()
        return self.current_display_text()

    # ======== Serialization ========= #

    def serialize_value(self) -> dict[str, typing.Any]:
        """Serialize the target by uuid, with its path relative to the owner's scope.

        Returns:
            dict[str, typing.Any]: uuid and path of the target.
        """
        target = self.target
        if target is None:
            return {
                self.TARGET_UUID_KEY: str(self._target_uuid)
                if self._target_uuid
                else None,
                self.TARGET_PATH_KEY: self.raw_value,
            }
        relative_path = StagePathResolver.compute_relative_path(
            self.node.scope, target.path
        )
        return {
            self.TARGET_UUID_KEY: str(target.uuid),
            self.TARGET_PATH_KEY: relative_path.as_posix(),
        }

    def restore_value(
        self,
        serialized_value: typing.Any,
        context: NodeDeserializationContext | None,
    ) -> None:
        """Set the reference from serialized data, re-pointing it at copies.

        Args:
            serialized_value (typing.Any): value from `serialize_value`, or just a path
                (plain value components of older files).
            context (NodeDeserializationContext | None): deserialization context.
        """
        serialized_uuid = None
        text = serialized_value
        if isinstance(serialized_value, dict):
            text = serialized_value.get(self.TARGET_PATH_KEY)
            raw_uuid = serialized_value.get(self.TARGET_UUID_KEY)
            serialized_uuid = self.as_uuid(raw_uuid) if raw_uuid else None

        # Not `push_value`: the text can name the original of a copy being made.
        NodeComponent.push_value(self, text, evaluate=False)
        self._target_uuid = serialized_uuid
        self._refresh_cached_values()

        if context is not None and serialized_uuid is not None:
            context.defer(lambda: self._remap_target(serialized_uuid, context))

    def _remap_target(
        self, serialized_uuid: UUID, context: NodeDeserializationContext
    ) -> None:
        """Point at the copy of the serialized target, if it was created in this run.

        Args:
            serialized_uuid (UUID): uuid of the target in the serialized data.
            context (NodeDeserializationContext): deserialization context.
        """
        new_uuid = context.resolve(serialized_uuid)
        if new_uuid is not None:
            self._target_uuid = new_uuid
        self._refresh_cached_values()
