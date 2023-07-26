import typing
import pathlib
from collections import OrderedDict
from PySide2 import QtWidgets
from nyx import get_main_logger
from nyx.core.constants import NyxFileExtensions, NyxFileFilters
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
            parent=main_window, caption=f"Export {node.name} as...", filter=NyxFileFilters.NYX_NODE_FILTER.value)
        if not file_path:
            return
        node.export_to_json(file_path)
        LOGGER.info(f"Exported node {file_path}")
    else:
        dir_path = QtWidgets.QFileDialog.getExistingDirectory(
            parent=main_window, caption="Select export directory")
        for node in selected_nodes:
            file_path = (pathlib.Path(
                dir_path) / node.name).with_suffix(NyxFileExtensions.NYX_NODE_FILE.value)
            node.export_to_json(file_path)
            LOGGER.info(f"Exported node {file_path}")


def _import_nodes(
    stage_graph: "StageGraphEditor",
    file_paths: "Collection[str] | Collection[pathlib.Path]"
):
    serialized_nodes = []
    for path in file_paths:
        path = pathlib.Path(path)
        if path.suffix == NyxFileExtensions.NYX_NODE_FILE.value:
            node_data = file_fn.load_json(path, object_pairs_hook=OrderedDict)
        elif path.suffix == NyxFileExtensions.NYX_STAGE_FILE.value:
            stage_data = file_fn.load_json(path, object_pairs_hook=OrderedDict)
            stage_node = Stage.convert_stage_to_node(
                stage_data, name=path.name)
            node_data = stage_node.serialize()
            stage_node.stage.deleteLater()
        serialized_nodes.append(node_data)

    paste_position = stage_graph.gr_view.get_center_position()
    parent_node_path = stage_graph.get_scope_path()
    paste_command = commands.PasteNodesCommand(
        stage=stage_graph.stage,
        serialize_nodes=serialized_nodes,
        position=paste_position,
        parent_node=parent_node_path
    )
    if len(serialized_nodes) == 1:
        paste_command.setText(
            f"Import node ({parent_node_path / serialized_nodes[0].get('name')})")
    else:
        paste_command.setText("Import nodes")
    stage_graph.stage.undo_stack.push(paste_command)


def import_nodes_from_explorer():
    """Select nodes from file explorer and import."""
    main_window = pyside_fn.find_nyx_editor_window()
    stage_graph = main_window.current_stage_graph
    if not stage_graph:
        return

    file_paths, _ = QtWidgets.QFileDialog.getOpenFileNames(parent=main_window,
                                                           caption="Import nodes",
                                                           filter=NyxFileFilters.NYX_STAGE_AND_NODES.value)
    if not file_paths:
        return

    _import_nodes(stage_graph, file_paths)
