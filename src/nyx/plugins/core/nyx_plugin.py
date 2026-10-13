import typing
import logging

from .resources import resources_rc  # noqa: F401
from nyx.api.v1 import NyxPluginManager, NyxPlugin

from .node_components.comment import CommentComponent
from .node_components.value import ValueComponent
from .node_components.flow import FlowComponent
from .node_components.script import ScriptComponent

from .nodes.blank import BlankNode
from .nodes.setter import SetterNode
from .nodes.getter import GetterNode
from .nodes.branch import BranchNode
from .nodes.flow_start import FlowStartNode
from .nodes.action import ActionNode
from .nodes.sequence import SequenceNode
from .nodes.log import LogNode


LOGGER = logging.getLogger(__name__)


@NyxPluginManager.register_plugin()
class NyxCore(NyxPlugin):
    @classmethod
    def get_type_id(cls) -> str:
        return "NyxCore"

    @classmethod
    def initialize(cls) -> typing.Self:
        plugin = cls()
        plugin.contents.node_components = [
            CommentComponent,
            FlowComponent,
            ValueComponent,
            ScriptComponent,
        ]
        plugin.contents.nodes = [
            BlankNode,
            SetterNode,
            GetterNode,
            ActionNode,
            BranchNode,
            FlowStartNode,
            SequenceNode,
            LogNode,
        ]

        return plugin
