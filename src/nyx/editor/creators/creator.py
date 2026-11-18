from __future__ import annotations

import dataclasses
import typing

from PySide6 import QtCore

if typing.TYPE_CHECKING:
    from nyx.core.node import Node
    from nyx.core.stage import Stage
    from nyx.core.stage_object import StageObject
    from nyx.editor.widgets.stage_graph_editor import StageGraphEditor


@dataclasses.dataclass(frozen=True)
class CreatorContext:
    """Where and with what a creator is asked to create something.

    Attributes:
        graph_editor: editor of the graph the user is in.
        stage: stage of the editor.
        scope_node: node whose contents are drawn, the new object goes in it.
        position: place the user asked for, in scene coordinates.
        selection_rect: area taken by the selected nodes in scene coordinates, None
            when no node is selected.
    """

    graph_editor: StageGraphEditor
    stage: Stage
    scope_node: Node
    position: QtCore.QPointF
    selection_rect: QtCore.QRectF | None = None

    @property
    def is_scope_locked(self) -> bool:
        """bool: nothing can be added to the scope, it belongs to a reference."""
        return self.scope_node.locks_children


class Creator:
    """Base of the entries listed in the Create menu of the graph view.

    A creator adds something to the stage when the user picks it: a note, a node
    preset, a whole subgraph. Creators are registered by id, the editor lists them in
    the order of registration and calls `create` with the context of the click. Use
    `UtilObjectCreator` to add util objects.

    Subclasses implement `get_type_id`, `get_display_name` and `create`. They change the
    stage by pushing commands, so the creation can be undone.
    """

    @classmethod
    def get_type_id(cls) -> str:
        """str: unique id of the creator. Subclasses must implement."""
        raise NotImplementedError

    @classmethod
    def get_display_name(cls) -> str:
        """str: text of the menu entry. Subclasses must implement."""
        raise NotImplementedError

    @classmethod
    def get_icon(cls) -> str:
        """str: resource path of the icon of the menu entry."""
        return ":/icons/plus"

    @classmethod
    def get_description(cls) -> str:
        """str: tooltip of the menu entry, empty for none."""
        return ""

    @classmethod
    def is_available(cls, context: CreatorContext) -> bool:
        """Check whether the creator can be used where the user is.

        Args:
            context (CreatorContext): where the user wants to create.

        Returns:
            bool: the menu entry is enabled. Defaults to the scope accepting new
                objects.
        """
        return not context.is_scope_locked

    @classmethod
    def create(cls, context: CreatorContext) -> StageObject | None:
        """Create something. Subclasses must implement.

        Args:
            context (CreatorContext): where the user wants to create.

        Returns:
            StageObject | None: created node or util object, which the editor
                selects. None if there is nothing to select.
        """
        raise NotImplementedError
