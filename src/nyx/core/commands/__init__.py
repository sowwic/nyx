from ._base_nyx_command import NyxCommand
from .create_node import CreateNodeCommand
from .delete_node import DeleteNodeCommand
from .rename_node import RenameNodeCommand
from .set_node_active_state import SetNodeActiveStateCommand
from .paste_nodes import PasteNodesCommand
from .move_node import MoveNodeCommand

# TODO: Remove once all references to attributes are removed
from .deprecated import (
    AddNodeAttributeCommand,
    DeleteNodeAttributeCommand,
    RenameNodeAttributeCommand,
    SetNodeAttributeCommand,
    ConnectAttributeCommand,
    SetNodeExecStartCommand,
    ConnectNodeExecCommand,
    DisconnectNodeInputExecCommand,
    SetNodeCommentCommand,
)

__all__ = [
    "NyxCommand",
    "CreateNodeCommand",
    "DeleteNodeCommand",
    "RenameNodeCommand",
    "SetNodeActiveStateCommand",
    "PasteNodesCommand",
    "MoveNodeCommand",
    # TODO: Remove once deprecated
    "AddNodeAttributeCommand",
    "DeleteNodeAttributeCommand",
    "RenameNodeAttributeCommand",
    "SetNodeAttributeCommand",
    "ConnectAttributeCommand",
    "SetNodeExecStartCommand",
    "ConnectNodeExecCommand",
    "DisconnectNodeInputExecCommand",
    "SetNodeCommentCommand",
]
