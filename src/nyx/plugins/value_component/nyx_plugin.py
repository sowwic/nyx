import typing
import logging
from nyx.api.v1 import plugin_manager, NyxPluginInterface

from .node_component import ValueComponent


LOGGER = logging.getLogger(__name__)


@plugin_manager.register_plugin()
class NyxCoreComponents(NyxPluginInterface):
    NAME = "NyxCoreComponents"

    @classmethod
    def initialize(cls) -> typing.Self:
        plugin = cls()
        plugin.contents.node_components = [ValueComponent]

        return plugin
