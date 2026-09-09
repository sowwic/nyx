import dataclasses
from typing import Self

from nyx.api.v1 import NodeComponent


@dataclasses.dataclass()
class NyxPluginContents:
    node_components: list[type[NodeComponent]] = dataclasses.field(
        init=False, default_factory=list
    )


class NyxPluginInterface:
    NAME: str = ""

    def __init__(self):
        self.contents = NyxPluginContents()

    @classmethod
    def initialize(cls) -> Self:
        raise NotImplementedError(
            "NyxPluginInterface based class must implement initialize() class method"
        )
