import dataclasses
import typing

if typing.TYPE_CHECKING:
    from nyx.api.v1 import Node, NodeComponent


@dataclasses.dataclass()
class NyxPluginContents:
    """Container for plugin contents information.

    Expected to be populated during plugin's `initialize` method.

    Attributes:
        node_components: List of NodeComponent classes
    """

    namespace: str = ""
    node_components: list[type[NodeComponent]] = dataclasses.field(
        init=False, default_factory=list
    )
    nodes: list[type[Node]] = dataclasses.field(init=False, default_factory=list)


class NyxPluginInterface:
    """Base interface for all Nyx plugins.

    Attributes:
        NAME: Plugin name (used as registry key)
        contents: NyxPluginContents instance
    """

    NAME: str = ""

    def __init__(self):
        self.contents = NyxPluginContents()

    @classmethod
    def initialize(cls) -> typing.Self:
        raise NotImplementedError(
            "NyxPluginInterface based class must implement initialize() class method"
        )
