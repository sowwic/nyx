import typing
import logging

from .resources import resources_rc  # noqa: F401
from nyx.api.v1 import NyxPluginManager, NyxPlugin

from .node_components.comment import CommentComponent
from .node_components.value import ValueComponent
from .node_components.flow import FlowComponent
from .node_components.script import ScriptComponent
from .node_components.file import FileComponent
from .node_components.stage_reference import StageReferenceComponent

from .nodes.blank import BlankNode
from .nodes.setter import SetterNode
from .nodes.getter import GetterNode
from .nodes.value import ValueNode
from .nodes.branch import BranchNode
from .nodes.for_loop import ForLoopNode
from .nodes.for_each_loop import ForEachLoopNode
from .nodes.flow_start import FlowStartNode
from .nodes.while_loop import WhileLoopNode
from .nodes.action import ActionNode
from .nodes.sequence import SequenceNode
from .nodes.log import LogNode
from .nodes.type_cast import TypeCastNode
from .nodes.get_type import GetTypeNode
from .nodes.reference import ReferenceNode


LOGGER = logging.getLogger(__name__)


@NyxPluginManager.register_plugin()
class NyxCore(NyxPlugin):
    """Built-in plugin providing the core nodes and node components."""

    QML_MODULE_NAME = "NyxCore"

    @classmethod
    def get_type_id(cls) -> str:
        """str: plugin id."""
        return "NyxCore"

    @classmethod
    def get_palette_name(cls) -> str:
        """str: name of the palette section."""
        return "Core"

    @classmethod
    def initialize(cls) -> typing.Self:
        """Create the plugin and list its nodes and components.

        Returns:
            typing.Self: initialized plugin.
        """
        plugin = cls()
        plugin.contents.node_components = [
            CommentComponent,
            FlowComponent,
            ValueComponent,
            ScriptComponent,
            FileComponent,
            StageReferenceComponent,
        ]
        plugin.contents.nodes = [
            BlankNode,
            SetterNode,
            GetterNode,
            ActionNode,
            ValueNode,
            BranchNode,
            ForLoopNode,
            ForEachLoopNode,
            WhileLoopNode,
            FlowStartNode,
            SequenceNode,
            LogNode,
            TypeCastNode,
            GetTypeNode,
            ReferenceNode,
        ]

        return plugin
