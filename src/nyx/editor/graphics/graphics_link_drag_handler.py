import dataclasses
import logging
import typing
from uuid import UUID

from PySide6 import QtCore

from nyx.core import commands
from nyx.core.exceptions import NyxCommandValidationError, StageObjectQueryError
from nyx.editor.graphics.graphics_link import GraphicsLink
from nyx.editor.graphics.graphics_node import GraphicsNode
from nyx.editor.graphics.graphics_plug import GraphicsPlug

if typing.TYPE_CHECKING:
    from nyx.core.node import Node
    from nyx.core.node_component import NodeComponent
    from nyx.editor.graphics.graphics_stage import GraphicsStage

LOGGER = logging.getLogger(__name__)


@dataclasses.dataclass
class LinkDragContext:
    """State of one link drag, passed around by `GraphicsLinkDragHandler`.

    Anything a step of the drag needs to know belongs here, so steps keep taking
    a single argument as the drag learns new things.

    Attributes:
        origin_plug: plug the dragged link comes out of. Dragging a linked input
            socket picks up the link, so this is the source plug of that link;
            for a picked output link it is the target plug.
        origin_socket: socket of the origin plug the drag is attached to.
        picked_link: existing link picked up from a socket, hidden while
            it is dragged.
        preview: link following the cursor.
    """

    origin_plug: GraphicsPlug
    origin_socket: GraphicsPlug.Socket
    picked_link: GraphicsLink | None = None
    preview: GraphicsLink | None = None

    @property
    def origin_component_uuid(self) -> UUID:
        """UUID: uuid of the component the drag started at. Outlives the plug."""
        return self.origin_plug.uuid

    @property
    def replaced_link_uuid(self) -> UUID | None:
        """UUID | None: uuid of the link being moved by the drag, if any."""
        return self.picked_link.uuid if self.picked_link is not None else None

    @property
    def from_output(self) -> bool:
        """bool: the drag comes out of an output socket."""
        return self.origin_socket is GraphicsPlug.Socket.OUTPUT

    @property
    def wanted_socket(self) -> GraphicsPlug.Socket:
        """GraphicsPlug.Socket: kind of socket the link can be dropped on."""
        return (
            GraphicsPlug.Socket.INPUT if self.from_output else GraphicsPlug.Socket.OUTPUT
        )


class GraphicsLinkDragHandler(QtCore.QObject):
    """Drags a link out of a socket of a plug and turns the drop into a command.

    Owns the state of the drag. The stage only forwards the calls of the plugs
    to it, and it adds and removes its preview item in the stage.

    `drag_changed` is emitted when the drag ends before a link is created, so
    whoever listens is already back to normal when the command is pushed.
    """

    drag_changed = QtCore.Signal(bool)
    """Emitted with True when a drag starts and False when it ends."""

    def __init__(self, gr_stage: GraphicsStage):
        """Initialize GraphicsLinkDragHandler.

        Args:
            gr_stage (GraphicsStage): stage the links are dragged in.
        """
        super().__init__(gr_stage)
        self._gr_stage = gr_stage
        self._context: LinkDragContext | None = None

    @property
    def is_dragging(self) -> bool:
        """bool: a link is being dragged from a socket."""
        return self._context is not None

    @property
    def context(self) -> LinkDragContext | None:
        """LinkDragContext | None: state of the running drag."""
        return self._context

    @property
    def preview(self) -> GraphicsLink | None:
        """GraphicsLink | None: link following the cursor while dragging."""
        return self._context.preview if self._context is not None else None

    def begin(self, plug: GraphicsPlug, socket: GraphicsPlug.Socket):
        """Start dragging a link from a socket of a plug.

        Dragging from a linked input socket picks up that link instead of making
        a new one: the drag continues from the source of the link, and dropping
        it elsewhere moves the link there. The same goes for the output socket of
        a component allowing a single output link, which is always linked when
        it is dragged from.

        Args:
            plug (GraphicsPlug): plug the drag starts at.
            socket (GraphicsPlug.Socket): socket the drag starts at.
        """
        self.cancel()
        picked = None
        if socket is GraphicsPlug.Socket.INPUT:
            picked = next(
                (link for link in plug.links if link.target_plug is plug), None
            )
            if picked is not None:
                picked.setVisible(False)
                plug, socket = picked.source_plug, GraphicsPlug.Socket.OUTPUT
        elif plug.component.single_output:
            picked = next(
                (link for link in plug.links if link.source_plug is plug), None
            )
            if picked is not None:
                picked.setVisible(False)
                plug, socket = picked.target_plug, GraphicsPlug.Socket.INPUT

        context = LinkDragContext(plug, socket, picked_link=picked)
        context.preview = GraphicsLink(
            source_plug=plug if context.from_output else None,
            target_plug=None if context.from_output else plug,
        )
        anchor = plug.output_anchor() if context.from_output else plug.input_anchor()
        context.preview.set_floating_pos(anchor)
        self._gr_stage.addItem(context.preview)
        self._context = context
        self.drag_changed.emit(True)

    def update(self, scene_pos: QtCore.QPointF):
        """Move the open end of the dragged link.

        Args:
            scene_pos (QtCore.QPointF): scene position of the cursor.
        """
        if self._context is not None:
            self._context.preview.set_floating_pos(scene_pos)

    def cancel(self):
        """Drop the dragged link without linking anything."""
        context, self._context = self._context, None
        if context is None:
            return
        if context.picked_link is not None:
            context.picked_link.setVisible(True)
        if context.preview.scene() is self._gr_stage:
            self._gr_stage.removeItem(context.preview)
        self.drag_changed.emit(False)

    def finish(self, scene_pos: QtCore.QPointF):
        """Finish dragging: link to the socket under the cursor or open the palette.

        Releasing on a socket that doesn't accept the link, or on a node, cancels
        the drag. Releasing on empty space opens the nodes palette, and the node
        created there gets linked to the socket the drag started at.

        Args:
            scene_pos (QtCore.QPointF): scene position of the release.
        """
        context = self._context
        self.cancel()
        if context is None:
            return

        over_node = False
        for item in self._gr_stage.items(scene_pos):
            if isinstance(item, GraphicsPlug):
                if item.socket_at(scene_pos) is context.wanted_socket:
                    self._link_plugs(context, item)
                    return
            elif isinstance(item, GraphicsNode):
                over_node = True

        if not over_node:
            # Not inside the mouse event: the palette runs a modal event loop.
            QtCore.QTimer.singleShot(0, lambda: self._open_palette(context))

    def _link_plugs(self, context: LinkDragContext, other_plug: GraphicsPlug):
        """Link the dragged plug to the plug it was dropped on, if that is allowed.

        Args:
            context (LinkDragContext): state of the drag.
            other_plug (GraphicsPlug): plug the link was dropped on.
        """
        if context.from_output:
            source, target = context.origin_plug.component, other_plug.component
        else:
            source, target = other_plug.component, context.origin_plug.component
        self._push_link_command(context, source, target)

    def _push_link_command(
        self, context: LinkDragContext, source: NodeComponent, target: NodeComponent
    ) -> bool:
        """Push a command linking two components if the link is allowed.

        When the drag moves an existing link, that link is removed in the same
        undo step.

        Args:
            context (LinkDragContext): state of the drag.
            source (NodeComponent): component providing output.
            target (NodeComponent): component accepting input.

        Returns:
            bool: link was created.
        """
        stage = self._gr_stage.stage
        if not self._gr_stage.can_link(source, target):
            LOGGER.debug(f"Components can't be linked: {source} -> {target}")
            return False
        try:
            link_command = commands.LinkNodeComponentsCommand(
                stage=stage, source=source, target=target
            )
            replaced_uuid = context.replaced_link_uuid
            if (
                replaced_uuid is None
                or replaced_uuid in link_command.replaced_link_uuids
            ):
                # Nothing to move, or the link command removes the link itself.
                stage.push_command(link_command)
            else:
                unlink_command = commands.UnlinkNodeComponentsCommand(
                    stage=stage, link_uuids=[replaced_uuid]
                )
                # Validate up front so a failure doesn't leave an empty macro.
                unlink_command.validate()
                link_command.validate()
                stage.undo_stack.beginMacro("Move link")
                try:
                    stage.push_command(unlink_command, link_command)
                finally:
                    stage.undo_stack.endMacro()
        except NyxCommandValidationError as error:
            LOGGER.warning(f"Failed to link {source} -> {target}: {error}")
            return False
        return True

    def _open_palette(self, context: LinkDragContext):
        """Show the nodes palette and link the created node to the dragged socket.

        Args:
            context (LinkDragContext): state of the drag.
        """
        # Imported here: the dialog imports views that import the graphics.
        from nyx.editor.widgets.dialogs.popup_nodes_palette import PopupNodesPalette

        PopupNodesPalette.popup(
            on_node_spawned=lambda node: self._link_spawned_node(context, node)
        )

    def _link_spawned_node(self, context: LinkDragContext, node: Node):
        """Link the first compatible component of a new node to the dragged socket.

        Args:
            context (LinkDragContext): state of the drag.
            node (Node): node created by the palette.
        """
        try:
            origin = self._gr_stage.stage.get_object(context.origin_component_uuid)
        except StageObjectQueryError:
            return
        for component in node.components_model.list_components():
            source, target = (
                (origin, component) if context.from_output else (component, origin)
            )
            if self._gr_stage.can_link(source, target):
                self._push_link_command(context, source, target)
                return
        LOGGER.debug(f"{node.path} has no component to link to {origin}")
