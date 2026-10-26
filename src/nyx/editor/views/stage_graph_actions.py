import functools
import logging
import typing

from PySide6 import QtCore, QtGui, QtWidgets

from nyx.core import commands
from nyx.core.exceptions import NyxCommandValidationError
from nyx.editor.core.action_router import ACTION_ROUTER
from nyx.editor.core.actions import ActionId
from nyx.editor.utils import clipboard
from nyx.editor.utils.common import get_app_config
from nyx.static.enums import CoreUtilObjects
from nyx.utils import pyside_fn

if typing.TYPE_CHECKING:
    from nyx.core import Node
    from nyx.editor.views.stage_graph_view import StageGraphView


LOGGER = logging.getLogger(__name__)


class StageGraphActions:
    """Editing actions of a stage graph view: nodes are copied, pasted, deleted, ...

    The actions work on the stage and the selection of the scene. The view only supplies
    the mouse position, the conditions telling when an action may run and the fitting of
    the viewport.
    """

    GROUP_MARGIN = 24.0
    """float: space between a new group and the nodes it is created around."""
    GROUP_TITLE_SPACE = 26.0
    """float: room above the nodes for the title of a new group."""
    DEFAULT_COLOR_FIELDS = {
        CoreUtilObjects.NOTE: "default_note_color",
        CoreUtilObjects.GROUP: "default_group_color",
    }
    """dict[str, str]: config value holding the default color of each util object."""

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
        self._create_util_object(
            CoreUtilObjects.NOTE, position=self._view.last_scene_mouse_pos
        )

    def create_group(self):
        """Create a group around the selected nodes, or at the mouse position."""
        gr_nodes = list(self._view.gr_stage.selected_gr_nodes())
        if not gr_nodes:
            self._create_util_object(
                CoreUtilObjects.GROUP, position=self._view.last_scene_mouse_pos
            )
            return

        bounds = QtCore.QRectF()
        for gr_node in gr_nodes:
            bounds = bounds.united(
                QtCore.QRectF(
                    gr_node.pos(), QtCore.QSizeF(gr_node.width, gr_node.height)
                )
            )
        margin = self.GROUP_MARGIN
        bounds = bounds.adjusted(
            -margin, -margin - self.GROUP_TITLE_SPACE, margin, margin
        )
        self._create_util_object(
            CoreUtilObjects.GROUP, position=bounds.topLeft(), size=bounds.size()
        )

    def _default_properties(self, type_id) -> dict[str, str]:
        """Get the properties new util objects of a type start with, from the config.

        Args:
            type_id (str): util object type id.

        Returns:
            dict[str, str]: the configured color, empty if the type has none or the
                configured value isn't a color, so the default of the type is used.
        """
        field = self.DEFAULT_COLOR_FIELDS.get(type_id)
        if field is None:
            return {}
        color = getattr(get_app_config().values.editor_widgets.graphics_stage, field)
        if not QtGui.QColor(color).isValid():
            LOGGER.warning(f"Invalid {field} {color!r} in the config, using the default")
            return {}
        return {"color": color}

    def _create_util_object(self, type_id, position, size=None):
        """Create a util object in the scope being drawn and select it.

        Args:
            type_id (str): util object type id.
            position (QtCore.QPointF): top left corner.
            size (QtCore.QSizeF | None): size, the default of the type if omitted.
        """
        view = self._view
        if not view.stage:
            return

        scope_node = view.stage.get_object(view.graph_editor.get_scope_path())
        command = commands.CreateUtilObjectCommand(
            view.stage,
            type_id,
            node=scope_node,
            position=position,
            size=size,
            properties=self._default_properties(type_id),
        )
        try:
            view.stage.push_command(command)
        except NyxCommandValidationError as err:
            LOGGER.warning(f"Can't create {type_id}: {err}")
            return

        view.gr_stage.rebuild_current_scope()
        view.gr_stage.clearSelection()
        gr_util = view.gr_stage.get_gr_util_object(command.result_object)
        if gr_util is not None:
            gr_util.setSelected(True)

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
