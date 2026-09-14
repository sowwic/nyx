import typing
import logging
from nyx.api.v1 import NyxPluginManager, NyxPluginInterface

from .node_components.value import ValueComponent
from .node_components.flow import FlowComponent
from .nodes.branch import BranchNode
from .nodes.flow_start import FlowStartNode


LOGGER = logging.getLogger(__name__)


@NyxPluginManager.register_plugin()
class NyxCore(NyxPluginInterface):
    NAME = "NyxCore"

    @classmethod
    def initialize(cls) -> typing.Self:
        plugin = cls()
        plugin.contents.namespace = "core"
        plugin.contents.node_components = [FlowComponent, ValueComponent]
        plugin.contents.nodes = [BranchNode, FlowStartNode]

        return plugin
