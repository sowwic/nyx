import logging
import pathlib
import typing
from collections import OrderedDict

from PySide6 import QtWidgets

from ...core import commands
from ...static.vars import NYX_FILE_FILTER, NYX_FILE_EXTENSION
from ...utils import file_fn, pyside_fn
from ...utils.profiling import profile

if typing.TYPE_CHECKING:
    from collections.abc import Collection
    from nyx.editor.widgets.stage_graph_editor import StageGraphEditor


LOGGER = logging.getLogger(__name__)


def export_selected_nodes():
    """Export selected nodes from stage_graph."""
    main_window = pyside_fn.find_nyx_editor_window()
    selected_nodes = main_window.stage_tree_view.selected_nodes()
    if not selected_nodes:
        return
    elif len(selected_nodes) == 1:
        node = selected_nodes[-1]
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            parent=main_window,
            caption=f"Export {node.name} as...",
            filter=NYX_FILE_FILTER,
        )
        if not file_path:
            return
        node.export_to_json(file_path)
        LOGGER.info(f"Exported node {file_path}")
    else:
        dir_path = QtWidgets.QFileDialog.getExistingDirectory(
            parent=main_window, caption="Select export directory"
        )
        for node in selected_nodes:
            file_path = (pathlib.Path(dir_path) / node.name).with_suffix(
                NYX_FILE_EXTENSION
            )
            node.export_to_json(file_path)
            LOGGER.info(f"Exported node {file_path}")


@profile(name="Nodes imported", text="{name} in {seconds:.4f}s")
def _import_nodes(
    stage_graph: StageGraphEditor,
    file_paths: Collection[str] | Collection[pathlib.Path],
    as_reference=False,
):
    serialized_nodes = []
    for path in file_paths:
        path = pathlib.Path(path)
        node_data = file_fn.load_json(path, object_pairs_hook=OrderedDict)
        # Add ref file path to node data.
        if as_reference:
            if stage_graph.stage.file_path == path:
                LOGGER.error(f"Can't reference file into itself: {path}")
                return
            node_data["reference_file_path"] = path.as_posix()
        serialized_nodes.append(node_data)

    # Paste command
    paste_position = stage_graph.gr_view.get_center_position()
    parent_node = stage_graph.stage.get_object(stage_graph.get_scope_path())
    paste_command = commands.PasteNodesCommand(
        stage=stage_graph.stage,
        serialize_nodes=serialized_nodes,
        position=paste_position,
        parent_node=parent_node,
    )
    command_name = "Reference" if as_reference else "Import"
    if len(serialized_nodes) == 1:
        parent_node_path = (
            parent_node.path if parent_node else stage_graph.stage.root_node.path
        )
        paste_command.setText(
            f"{command_name} node ({parent_node_path / serialized_nodes[0].get('name')})"
        )
    else:
        paste_command.setText(f"{command_name} nodes")
    stage_graph.stage.push_command(paste_command)


def import_nodes_from_explorer(as_reference=False):
    """Select nodes from file explorer and import."""
    main_window = pyside_fn.find_nyx_editor_window()
    stage_graph = main_window.current_stage_graph
    if not stage_graph:
        return

    file_paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
        parent=main_window, caption="Select nodes", filter=NYX_FILE_FILTER
    )
    if not file_paths:
        return

    _import_nodes(stage_graph, file_paths, as_reference=as_reference)
