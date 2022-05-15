import typing
import json
from collections import (OrderedDict,
                         Sequence)
from PySide2 import QtWidgets

from nyx.core import commands
from nyx import get_main_logger

if typing.TYPE_CHECKING:
    from nyx.core import Stage
    from nyx.core import Node


LOGGER = get_main_logger()


def serialize_nodes_to_clipboard(nodes: "Sequence[Node]", delete=False):
    data = {}
    serialized_nodes = []
    stage = nodes[0].stage
    # Serialize to clipboard
    for each_node in nodes:
        serialized_nodes.append(each_node.serialize())
    data["nyx_nodes"] = serialized_nodes
    serialized_str = json.dumps(data)
    QtWidgets.QApplication.clipboard().setText(serialized_str)

    # Cut operation
    if delete:
        del_cmd = commands.DeleteNodeCommand(stage=stage,
                                             nodes=nodes,
                                             command_text="Cut nodes")
        stage.undo_stack.push(del_cmd)


def deserialize_nodes_from_clipboard(stage: "Stage",
                                     hashmap: OrderedDict,
                                     new_parent: "Node" = None,
                                     restore_id: bool = True):
    pass
