import logging
import os
import pathlib
import typing
import uuid
from collections import OrderedDict

from PySide6 import QtWidgets

from ...core import commands
from ...core.node import Node
from ...static.vars import NYX_FILE_FILTER
from ...utils import file_fn, pyside_fn
from ...utils.profiling import profile
from ...static.enums import CoreNodes, RestoreUuidOption

if typing.TYPE_CHECKING:
    from collections.abc import Collection
    from nyx.core.stage import Stage
    from nyx.editor.widgets.stage_graph_editor import StageGraphEditor


LOGGER = logging.getLogger(__name__)


def _serialize_reference_node(stage: Stage, path: pathlib.Path) -> OrderedDict:
    """Compose the data of a reference node standing for a stage file.

    Args:
        stage (Stage): stage receiving the node.
        path (pathlib.Path): stage file to reference.

    Returns:
        OrderedDict: serialized reference node.
    """
    if stage.file_path is not None:
        source = pathlib.Path(
            os.path.relpath(path, pathlib.Path(stage.file_path).parent)
        )
    else:
        source = path
    return OrderedDict(
        [
            (Node.UUID_KEY, str(uuid.uuid4())),
            (Node.NAME_KEY, path.stem),
            (Node.TYPE_ID_KEY, CoreNodes.REFERENCE),
            (Node.ACTIVE_KEY, True),
            ("source", source.as_posix()),
        ]
    )


@profile(name="Stages imported", text="{name} in {seconds:.4f}s")
def _import_stages(
    stage_graph: StageGraphEditor,
    file_paths: Collection[str] | Collection[pathlib.Path],
    as_reference=False,
):
    """Import stage files into the active stage.

    Args:
        stage_graph (StageGraphEditor): editor receiving the stages.
        file_paths (Collection[str] | Collection[pathlib.Path]): files to import.
        as_reference (bool): reference the files instead of copying their content.
    """
    serialized_nodes = []
    for path in file_paths:
        path = pathlib.Path(path)
        if as_reference:
            if stage_graph.stage.file_path == path:
                LOGGER.error(f"Can't reference file into itself: {path}")
                return
            node_data = _serialize_reference_node(stage_graph.stage, path)
        else:
            node_data = file_fn.load_json(path, object_pairs_hook=OrderedDict)
        serialized_nodes.append(node_data)

    # Paste command
    paste_position = stage_graph.gr_view.get_center_position()
    parent_node = stage_graph.stage.get_object(stage_graph.get_scope_path())
    paste_command = commands.PasteNodesCommand(
        stage=stage_graph.stage,
        serialize_nodes=serialized_nodes,
        position=paste_position,
        parent_node=parent_node,
        restore_uuid=RestoreUuidOption.ATTEMPT_RESTORE,
    )
    command_name = "Reference" if as_reference else "Import"
    if len(serialized_nodes) == 1:
        parent_node_path = (
            parent_node.path if parent_node else stage_graph.stage.root_node.path
        )
        node_path = parent_node_path / serialized_nodes[0].get("name")
        paste_command.setText(f"{command_name} stage ({node_path})")
    else:
        paste_command.setText(f"{command_name} stages")
    stage_graph.stage.push_command(paste_command)


def import_stages_from_explorer(as_reference=False):
    """Select stage files from file explorer and import them."""
    main_window = pyside_fn.find_nyx_editor_window()
    stage_graph = main_window.current_stage_graph
    if not stage_graph:
        return

    file_paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
        parent=main_window, caption="Select stages", filter=NYX_FILE_FILTER
    )
    if not file_paths:
        return

    _import_stages(stage_graph, file_paths, as_reference=as_reference)
