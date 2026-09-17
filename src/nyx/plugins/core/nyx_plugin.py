import typing
import logging
from nyx.api.v1 import NyxPluginManager, NyxPluginInterface, Node

from .node_components.value import ValueComponent
from .node_components.flow import FlowComponent
from .nodes.branch import BranchNode
from .nodes.flow_start import FlowStartNode
from .nodes.action import ActionNode


LOGGER = logging.getLogger(__name__)


@NyxPluginManager.register_plugin()
class NyxCore(NyxPluginInterface):
    NAME = "NyxCore"

    @classmethod
    def initialize(cls) -> typing.Self:
        plugin = cls()
        plugin.contents.node_components = [FlowComponent, ValueComponent]
        plugin.contents.nodes = [Node, ActionNode, BranchNode, FlowStartNode]

        return plugin
