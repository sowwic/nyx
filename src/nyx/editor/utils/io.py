import typing
import pathlib
from collections import OrderedDict
from PySide2 import QtWidgets
from nyx import get_main_logger
from nyx.core import constants
from nyx.core import Stage
from nyx.core import commands
from nyx.utils import file_fn
from nyx.utils import pyside_fn


if typing.TYPE_CHECKING:
    from nyx.editor.widgets.stage_graph_editor import StageGraphEditor
    from collections.abc import Collection


LOGGER = get_main_logger()


def export_selected_nodes():
    """Export selected nodes from stage_graph."""
    main_window = pyside_fn.find_nyx_editor_window()
    selected_nodes = main_window.stage_tree_view.selected_nodes()
    if not selected_nodes:
        return
    elif len(selected_nodes) == 1:
        node = selected_nodes[-1]
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            parent=main_window, caption=f"Export {node.name} as...", filter=constants.NYX_FILE_FILTER)
        if not file_path:
            return
        node.export_to_json(file_path)
        LOGGER.info(f"Exported node {file_path}")
    else:
        dir_path = QtWidgets.QFileDialog.getExistingDirectory(
            parent=main_window, caption="Select export directory")
        for node in selected_nodes:
            file_path = (pathlib.Path(
                dir_path) / node.name).with_suffix(constants.NYX_FILE_EXTENSION)
            node.export_to_json(file_path)
            LOGGER.info(f"Exported node {file_path}")


def _import_nodes(
    stage_graph: "StageGraphEditor",
    file_paths: "Collection[str] | Collection[pathlib.Path]",
    as_reference=False
):
    serialized_nodes = []
    for path in file_paths:
        path = pathlib.Path(path)
        node_data = file_fn.load_json(path, object_pairs_hook=OrderedDict)
        if node_data["metadata"]["type"] == "stage":
            node_data = Stage.convert_stage_to_node(
                node_data, name=path.stem)
        # Add ref file path to node data.
        if as_reference:
            if stage_graph.stage.file_path == path:
                LOGGER.error(f"Can't reference file into itself: {path}")
                return
            node_data["reference_file_path"] = path.as_posix()
        serialized_nodes.append(node_data)

    # Paste command
    paste_position = stage_graph.gr_view.get_center_position()
    parent_node_path = stage_graph.get_scope_path()
    paste_command = commands.PasteNodesCommand(
        stage=stage_graph.stage,
        serialize_nodes=serialized_nodes,
        position=paste_position,
        parent_node=parent_node_path
    )
    command_name = "Reference" if as_reference else "Import"
    if len(serialized_nodes) == 1:
        paste_command.setText(
            f"{command_name} node ({parent_node_path / serialized_nodes[0].get('name')})")
    else:
        paste_command.setText(f"{command_name} nodes")
    stage_graph.stage.undo_stack.push(paste_command)


def import_nodes_from_explorer(as_reference=False):
    """Select nodes from file explorer and import."""
    main_window = pyside_fn.find_nyx_editor_window()
    stage_graph = main_window.current_stage_graph
    if not stage_graph:
        return

    file_paths, _ = QtWidgets.QFileDialog.getOpenFileNames(parent=main_window,
                                                           caption="Select nodes",
                                                           filter=constants.NYX_FILE_FILTER)
    if not file_paths:
        return

    _import_nodes(stage_graph, file_paths, as_reference=as_reference)
