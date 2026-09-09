import typing
import logging
from nyx.api.v1 import plugin_manager, NyxPluginInterface

from .node_component import ValueComponent


LOGGER = logging.getLogger(__name__)


@plugin_manager.register_plugin()
class NyxCoreComponents(NyxPluginInterface):
    NAME = "NyxCoreComponents"

    def __init__(self):
        self.node_components = [ValueComponent]
        LOGGER.info(self.node_components)

    @classmethod
    def initialize(cls) -> typing.Self:
        return cls()
