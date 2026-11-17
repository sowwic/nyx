"""Built-in node components, for plugins that subclass or reuse them."""

from nyx.stdlib.node_components.comment import CommentComponent
from nyx.stdlib.node_components.file import FileComponent
from nyx.stdlib.node_components.flow import FlowComponent
from nyx.stdlib.node_components.object_path import StageObjectPathComponent
from nyx.stdlib.node_components.remote_script import RemoteScriptComponent
from nyx.stdlib.node_components.script import ScriptComponent
from nyx.stdlib.node_components.value import ValueComponent

__all__ = [
    "CommentComponent",
    "FileComponent",
    "FlowComponent",
    "StageObjectPathComponent",
    "RemoteScriptComponent",
    "ScriptComponent",
    "ValueComponent",
]
