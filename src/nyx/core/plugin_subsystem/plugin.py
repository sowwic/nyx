from abc import ABC, abstractmethod
import dataclasses
import typing
import pathlib
import inspect


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


class NyxPlugin(ABC):
    """Base interface for all Nyx plugins.

    Attributes:
        NAME: Plugin name (used as registry key)
        contents: NyxPluginContents instance
    """

    QML_MODULE_NAME = ""
    QML_DIRECTORY_NAME = "qml"

    def __init__(self):
        self.contents = NyxPluginContents()

    @classmethod
    def path(cls) -> pathlib.Path:
        return pathlib.Path(inspect.getfile(cls))

    @classmethod
    def root_directory(cls) -> pathlib.Path:
        return cls.path().parent

    @classmethod
    def qml_directory(cls) -> pathlib.Path:
        return cls.root_directory() / "qml"

    @classmethod
    def resources_directory(cls) -> pathlib.Path:
        return cls.root_directory() / "resources"

    @classmethod
    def icons_directory(cls) -> pathlib.Path:
        return cls.resources_directory() / "icons"

    @classmethod
    def get_icon(cls, icon_name: str) -> pathlib.Path:
        return cls.icons_directory() / icon_name

    @classmethod
    @abstractmethod
    def initialize(cls) -> typing.Self:
        raise NotImplementedError(f"{cls.__name__} must implement initialize()")

    @classmethod
    def get_type_id(cls) -> str:
        return ""

    @classmethod
    def get_type_display_name(cls) -> str:
        return cls.get_type_id()

    @classmethod
    def get_tags(cls) -> set[str]:
        return set()
