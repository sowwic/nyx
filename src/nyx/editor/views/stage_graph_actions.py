import functools
import logging
import typing

from PySide6 import QtCore, QtGui, QtWidgets

from nyx.core import commands
from nyx.core.exceptions import NyxCommandValidationError
from nyx.core.plugin_subsystem.registry import NYX_REGISTRY
from nyx.core.util_object import UtilObject
from nyx.editor.core.action_registry import ACTION_REGISTRY
from nyx.editor.creators import Creator, CreatorContext
from nyx.editor.utils import context_menus
from nyx.editor.core.action_router import ACTION_ROUTER
from nyx.editor.core.actions import ActionId
from nyx.editor.utils import clipboard
from nyx.static.enums import CoreCreators
from nyx.utils import pyside_fn

if typing.TYPE_CHECKING:
    from nyx.core import Node
    from nyx.core.stage_object import StageObject
    from nyx.editor.views.stage_graph_view import StageGraphView


LOGGER = logging.getLogger(__name__)


class StageGraphActions:
    """Editing actions of a stage graph view: nodes are copied, pasted, deleted, ...

    The actions work on the stage and the selection of the scene. The view only supplies
    the mouse position, the conditions telling when an action may run and the fitting of
    the viewport.
    """

    CREATOR_ACTION_IDS: typing.ClassVar[dict[str, ActionId]] = {
        CoreCreators.NOTE: ActionId.CREATE_NOTE,
        CoreCreators.GROUP: ActionId.CREATE_GROUP,
    }
    """Creators that have a registered action, with its shortcut and condition."""

    def __init__(self, view: StageGraphView):
        """Initialize StageGraphActions.

        Args:
            view (StageGraphView): view the actions are for.
        """
        self._view = view

    def register(self):
        """Register the handlers of the actions, scoped to the view."""
        view = self._view
        register = functools.partial(ACTION_ROUTER.register_handler, scope=view)
        register(
            ActionId.CREATE_NODE, view.create_new_node, condition=view.idle_condition
        )
        register(ActionId.CREATE_NOTE, self.create_note, condition=view.idle_condition)
        register(ActionId.CREATE_GROUP, self.create_group, condition=view.idle_condition)
        register(
            ActionId.PASTE,
            self.paste_nodes_from_clipboard,
            condition=view.idle_condition,
        )
        register(
            ActionId.COPY,
            self.copy_selected_nodes,
            condition=view.selection_editable_condition,
        )
        register(
            ActionId.CUT,
            self.cut_selected_nodes,
            condition=view.selection_editable_condition,
        )
        register(
            ActionId.DELETE,
            self.delete_selected,
            condition=view.selection_editable_condition,
        )
        register(
            ActionId.DELETE_NODE,
            self.delete_selected,
            condition=view.selection_editable_condition,
        )
        register(
            ActionId.COPY_NODE_PATH,
            self.copy_selected_node_path,
            condition=view.selection_editable_condition,
        )
        register(
            ActionId.RELOAD_REFERENCE,
            self.reload_selected_references,
            condition=view.selection_editable_condition,
        )
        register(
            ActionId.OPEN_REFERENCED_STAGE,
            self.open_selected_referenced_stages,
            condition=view.selection_editable_condition,
        )
        register(
            ActionId.FOCUS_SELECTED,
            self.focus_on_selected_nodes,
            condition=view.selection_editable_condition,
        )

    def delete_selected(self):
        """Delete the selected nodes and util objects through an undoable command."""
        view = self._view
        if not view.stage:
            return

        if view.gr_stage.is_selection_empty():
            LOGGER.warning("Nothing selected to delete!")
            return

        nodes_to_delete: list[Node] = [
            gr_node.node
            for gr_node in view.gr_stage.selected_gr_nodes()
            if not gr_node.node.is_in_locked_scope
        ]
        util_objects_to_delete = [
            gr_util.util_object
            for gr_util in view.gr_stage.selected_gr_util_objects()
            if not gr_util.util_object.is_locked
        ]
        delete_commands = []
        if nodes_to_delete:
            delete_commands.append(
                commands.DeleteNodeCommand(stage=view.stage, nodes=nodes_to_delete)
            )
        if util_objects_to_delete:
            delete_commands.append(
                commands.DeleteUtilObjectCommand(view.stage, util_objects_to_delete)
            )
        if not delete_commands:
            LOGGER.warning("Nodes of a reference can't be deleted")
            return

        undo_stack = view.stage.undo_stack
        if len(delete_commands) > 1:
            undo_stack.beginMacro("Delete selection")
        try:
            view.stage.push_command(*delete_commands)
        finally:
            if len(delete_commands) > 1:
                undo_stack.endMacro()
        view.gr_stage.rebuild_current_scope()

    def create_note(self):
        """Create a note at the mouse position."""
        self.run_creator(NYX_REGISTRY.get_creator_cls(CoreCreators.NOTE))

    def create_group(self):
        """Create a group around the selected nodes, or at the mouse position."""
        self.run_creator(NYX_REGISTRY.get_creator_cls(CoreCreators.GROUP))

    def build_creator_context(
        self, position: QtCore.QPointF | None = None
    ) -> CreatorContext | None:
        """Describe where creators would create something.

        Args:
            position (QtCore.QPointF | None): position in scene coordinates, the mouse
                position if omitted.

        Returns:
            CreatorContext | None: context, None if the view shows no stage.
        """
        view = self._view
        if not view.stage:
            return None
        selection_rect = None
        for gr_node in view.gr_stage.selected_gr_nodes():
            node_rect = QtCore.QRectF(
                gr_node.pos(), QtCore.QSizeF(gr_node.width, gr_node.height)
            )
            selection_rect = (
                node_rect if selection_rect is None else selection_rect.united(node_rect)
            )
        return CreatorContext(
            graph_editor=view.graph_editor,
            stage=view.stage,
            scope_node=view.stage.get_object(view.graph_editor.get_scope_path()),
            position=view.last_scene_mouse_pos if position is None else position,
            selection_rect=selection_rect,
        )

    def run_creator(
        self,
        creator_cls: type[Creator] | None,
        position: QtCore.QPointF | None = None,
        context: CreatorContext | None = None,
    ) -> StageObject | None:
        """Let a creator create something in the scope being drawn, and select it.

        Args:
            creator_cls (type[Creator] | None): creator to run, ignored if None.
            position (QtCore.QPointF | None): position in scene coordinates, the mouse
                position if omitted. Ignored when a context is given.
            context (CreatorContext | None): context to give the creator, built from the
                position if omitted.

        Returns:
            StageObject | None: created object, None if nothing was created.
        """
        if creator_cls is None:
            return None
        context = context or self.build_creator_context(position)
        if context is None:
            return None
        name = creator_cls.get_display_name()
        if not creator_cls.is_available(context):
            LOGGER.warning(f"Can't create {name.lower()} here")
            return None
        try:
            created = creator_cls.create(context)
        except NyxCommandValidationError as err:
            LOGGER.warning(f"Can't create {name.lower()}: {err}")
            return None

        view = self._view
        view.gr_stage.rebuild_current_scope()
        view.gr_stage.clearSelection()
        if isinstance(created, UtilObject):
            gr_util = view.gr_stage.get_gr_util_object(created)
            if gr_util is not None:
                gr_util.setSelected(True)
        elif created is not None:
            view.graph_editor.select_nodes([created])
        return created

    def build_creator_actions(
        self, parent: QtWidgets.QWidget, position: QtCore.QPointF
    ) -> list[QtGui.QAction]:
        """Make the menu entries of the creators.

        The note and group entries run the registered actions, which come with their
        shortcuts. The creators of plugins get an entry that runs them at the position.

        Args:
            parent (QtWidgets.QWidget): owner of the new actions.
            position (QtCore.QPointF): position in scene coordinates.

        Returns:
            list[QtGui.QAction]: entries, in the order the creators are registered.
        """
        context = self.build_creator_context(position)
        actions = []
        for creator_id, creator_cls in NYX_REGISTRY.creators.items():
            registered_action_id = self.CREATOR_ACTION_IDS.get(creator_id)
            if registered_action_id is not None:
                actions.append(
                    context_menus.make_proxy_action(
                        parent,
                        ACTION_REGISTRY.action(registered_action_id),
                        creator_cls.get_display_name(),
                        QtGui.QIcon(creator_cls.get_icon()),
                    )
                )
                continue
            action = QtGui.QAction(
                QtGui.QIcon(creator_cls.get_icon()),
                creator_cls.get_display_name(),
                parent,
            )
            action.setToolTip(creator_cls.get_description())
            action.setEnabled(context is not None and creator_cls.is_available(context))
            action.triggered.connect(
                lambda _checked=False, cls=creator_cls, ctx=context: self.run_creator(
                    cls, context=ctx
                )
            )
            actions.append(action)
        return actions

    def reload_selected_references(self):
        """Load the source files of the selected nodes again."""
        for gr_node in self._view.gr_stage.selected_gr_nodes():
            gr_node.node.reload_source()
        self._view.gr_stage.rebuild_current_scope()

    def open_selected_referenced_stages(self):
        """Open the source files of the selected nodes in the editor."""
        main_window = pyside_fn.find_nyx_editor_window()
        for gr_node in self._view.gr_stage.selected_gr_nodes():
            source_file = gr_node.node.get_source_file()
            if source_file is not None:
                main_window.on_stage_open_recent(str(source_file))

    def copy_selected_nodes(self):
        """Copy the selected nodes to the clipboard."""
        selected_nodes = [
            gr_node.node for gr_node in self._view.gr_stage.selected_gr_nodes()
        ]
        if not selected_nodes:
            return

        clipboard.serialize_nodes_to_clipboard(selected_nodes, delete=False)
        LOGGER.info("Copied selected nodes")

    def cut_selected_nodes(self):
        """Cut the selected nodes to the clipboard."""
        selected_nodes = [
            gr_node.node for gr_node in self._view.gr_stage.selected_gr_nodes()
        ]
        if not selected_nodes:
            return

        if any(node.is_in_locked_scope for node in selected_nodes):
            LOGGER.warning("Nodes of a reference can't be cut, copying them instead")
            clipboard.serialize_nodes_to_clipboard(selected_nodes, delete=False)
            return

        clipboard.serialize_nodes_to_clipboard(selected_nodes, delete=True)
        LOGGER.info("Cut selected nodes")

    def paste_nodes_from_clipboard(self):
        """Paste nodes from the clipboard into the current scope."""
        serialized_nodes = clipboard.get_serialized_nodes_from_clipboard()
        if not serialized_nodes:
            LOGGER.warning("No nodes found in the clipboard!")
            return

        view = self._view
        parent_node = view.stage.get_object(view.graph_editor.get_scope_path())
        paste_cmd = commands.PasteNodesCommand(
            stage=view.stage,
            serialize_nodes=serialized_nodes,
            position=view.last_scene_mouse_pos,
            parent_node=parent_node,
        )
        try:
            view.stage.push_command(paste_cmd)
        except NyxCommandValidationError as err:
            LOGGER.warning(str(err))

    def copy_selected_node_path(self):
        """Copy the path of the last selected node to the clipboard."""
        gr_node = self._view.gr_stage.get_last_selected_gr_node()
        if gr_node is None:
            return
        path = gr_node.node.path.as_posix()
        QtWidgets.QApplication.clipboard().setText(path)
        LOGGER.info(f"Copied node path: {path}")

    def focus_on_selected_nodes(self):
        """Center on the selected nodes, zooming so they fit in the view.

        If none of the selected nodes is in the current scope, the scope moves to
        the parent of the last selected one first.
        """
        view = self._view
        graph_editor = view.gr_stage.graph_editor
        selected_nodes = graph_editor.list_selected_nodes()
        nodes_in_scope = graph_editor.filter_nodes_by_scope(selected_nodes)
        if not nodes_in_scope and selected_nodes:
            graph_editor.set_scope_path(selected_nodes[-1].path.parent)
            graph_editor.select_nodes(selected_nodes)
            nodes_in_scope = graph_editor.filter_nodes_by_scope(selected_nodes)

        nodes_rect = QtCore.QRectF()
        for node in nodes_in_scope:
            gr_node = view.gr_stage.get_gr_node(node)
            if gr_node is not None:
                nodes_rect = nodes_rect.united(gr_node.sceneBoundingRect())

        if nodes_rect.isNull():
            return
        view.fit_scene_rect(nodes_rect)
