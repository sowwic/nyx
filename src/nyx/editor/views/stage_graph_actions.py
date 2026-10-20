import functools
import logging
import typing

from PySide6 import QtCore, QtWidgets

from nyx.core import commands
from nyx.editor.core.action_router import ACTION_ROUTER
from nyx.editor.core.actions import ActionId
from nyx.editor.utils import clipboard

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
            ActionId.FOCUS_SELECTED,
            self.focus_on_selected_nodes,
            condition=view.selection_editable_condition,
        )

    def delete_selected(self):
        """Delete the selected nodes through an undoable command."""
        view = self._view
        if not view.stage:
            return

        if view.gr_stage.is_gr_node_selection_empty():
            LOGGER.warning("No nodes selected to delete!")
            return

        selected_gr_nodes = view.gr_stage.selected_gr_nodes()
        nodes_to_delete: list[Node] = [gr_node.node for gr_node in selected_gr_nodes]
        del_cmd = commands.DeleteNodeCommand(stage=view.stage, nodes=nodes_to_delete)
        view.stage.push_command(del_cmd)
        view.gr_stage.rebuild_current_scope()

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
        view.stage.push_command(paste_cmd)

    def copy_selected_node_path(self):
        """Copy the path of the last selected node to the clipboard."""
        gr_node = self._view.gr_stage.get_last_selected_gr_node()
        if gr_node is None:
            return
        path = gr_node.node.path.as_posix()
        QtWidgets.QApplication.clipboard().setText(path)
        LOGGER.info(f"Copied node path: {path}")

    def focus_on_selected_nodes(self):
        """Center on the selected nodes, zooming so they fit in the view."""
        view = self._view
        graph_editor = view.gr_stage.graph_editor
        selected_nodes = graph_editor.list_selected_nodes()
        nodes_in_scope = graph_editor.filter_nodes_by_scope(selected_nodes)

        nodes_rect = QtCore.QRectF()
        for node in nodes_in_scope:
            gr_node = view.gr_stage.get_gr_node(node)
            if gr_node is not None:
                nodes_rect = nodes_rect.united(gr_node.sceneBoundingRect())

        if nodes_rect.isNull():
            return
        view.fit_scene_rect(nodes_rect)
