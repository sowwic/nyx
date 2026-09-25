import json
import logging
import typing
from collections import OrderedDict
from collections.abc import Sequence

from PySide6 import QtWidgets

from nyx.core import commands

if typing.TYPE_CHECKING:
    from nyx.core import Node


LOGGER = logging.getLogger(__name__)


def serialize_nodes_to_clipboard(nodes: Sequence[Node], delete: bool = False) -> None:
    """Serialize nodes to clipboard. If delete is True, perform cut operation.

    Args:
        nodes: Nodes to serialize.
        delete: Whether to delete nodes after serialization.
    """
    data = {}
    serialized_nodes = []
    stage = nodes[0].stage
    top_level_nodes = stage.filter_top_level_nodes(nodes)
    # Serialize to clipboard
    for each_node in top_level_nodes:
        serialized_nodes.append(each_node.serialize())
    data["nyx_nodes"] = serialized_nodes
    serialized_str = json.dumps(data)
    QtWidgets.QApplication.clipboard().setText(serialized_str)

    # Cut operation
    if delete:
        del_cmd = commands.DeleteNodeCommand(
            stage=stage, nodes=top_level_nodes, command_text="Cut nodes"
        )
        stage.push_command(del_cmd)


def get_serialized_nodes_from_clipboard() -> list[OrderedDict] | list:
    """Get serialized nodes from clipboard.
    Returns:
        list[OrderedDict] | list: List of serialized nodes or empty list.
    """
    raw_data = QtWidgets.QApplication.clipboard().text()
    serialized_nodes = []
    try:
        json_data: dict = json.loads(raw_data)
    except Exception:
        LOGGER.debug(f"Clipboard data is not of json format: {raw_data}")
    else:
        serialized_nodes: list[OrderedDict] = json_data.get("nyx_nodes", [])

    return serialized_nodes
