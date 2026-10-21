from abc import ABC, abstractmethod
import dataclasses
import types
import typing
import pathlib
import inspect


if typing.TYPE_CHECKING:
    from nyx.api.v1 import Node, NodeComponent, Datatype


@dataclasses.dataclass()
class NyxPluginContents:
    """Container for plugin contents information.

    Expected to be populated during plugin's `initialize` method.

    Attributes:
        node_components: List of NodeComponent classes
        nodes: List of Node classes
        datatypes: List of Datatype instances
    """

    namespace: str = ""
    node_components: list[type[NodeComponent]] = dataclasses.field(
        init=False, default_factory=list
    )
    nodes: list[type[Node]] = dataclasses.field(init=False, default_factory=list)
    datatypes: list[Datatype] = dataclasses.field(init=False, default_factory=list)

    def register_function_node(
        self,
        func: typing.Callable,
        type_id: str | None = None,
        tags: typing.Iterable[str] = (),
    ) -> type[Node]:
        """Add a node calling a function.

        The node has a value component for every parameter and one for the return
        value, the datatypes are chosen from the type hints of the function.

        Args:
            func (typing.Callable): function to call.
            type_id (str | None): node type id. Derived from the module and name of
                the function if omitted.
            tags (typing.Iterable[str]): tags of the node besides "function".

        Raises:
            TypeError: func is not a named function.
            ValueError: a node with the same type id is already in the contents.

        Returns:
            type[Node]: generated node class.
        """
        from ..function_node import create_function_node_class

        node_cls = create_function_node_class(func, type_id=type_id, tags=tags)
        if any(node.get_type_id() == node_cls.get_type_id() for node in self.nodes):
            raise ValueError(f"Node {node_cls.get_type_id()} is already registered")
        self.nodes.append(node_cls)
        return node_cls

    def register_function_module(
        self, module: types.ModuleType, namespace: str
    ) -> list[type[Node]]:
        """Add a node for every public function of a module.

        Args:
            module (types.ModuleType): module defining the functions.
            namespace (str): prefix of the node type ids, `function:<namespace>.<name>`.
                Keeps the nodes of a plugin apart from functions with the same name in
                other plugins. Also a tag of the nodes.

        Returns:
            list[type[Node]]: generated node classes.
        """
        from ..function_node import find_public_functions

        return [
            self.register_function_node(
                function,
                type_id=f"function:{namespace}.{function.__name__}",
                tags=(namespace,),
            )
            for function in find_public_functions(module)
        ]


class NyxPlugin(ABC):
    """Base interface for all Nyx plugins.

    Attributes:
        NAME: Plugin name (used as registry key)
        contents: NyxPluginContents instance
    """

    QML_MODULE_NAME = ""
    QML_DIRECTORY_NAME = "qml"

    def __init__(self):
        """Initialize NyxPlugin with empty contents."""
        self.contents = NyxPluginContents()

    @classmethod
    def path(cls) -> pathlib.Path:
        """Get the plugin source file.

        Returns:
            pathlib.Path: file defining the plugin class.
        """
        return pathlib.Path(inspect.getfile(cls))

    @classmethod
    def root_directory(cls) -> pathlib.Path:
        """pathlib.Path: directory containing the plugin."""
        return cls.path().parent

    @classmethod
    def qml_directory(cls) -> pathlib.Path:
        """pathlib.Path: plugin QML directory."""
        return cls.root_directory() / "qml"

    @classmethod
    def resources_directory(cls) -> pathlib.Path:
        """pathlib.Path: plugin resources directory."""
        return cls.root_directory() / "resources"

    @classmethod
    def icons_directory(cls) -> pathlib.Path:
        """pathlib.Path: plugin icons directory."""
        return cls.resources_directory() / "icons"

    @classmethod
    def get_icon(cls, icon_name: str) -> pathlib.Path:
        """Get the path of a plugin icon.

        Args:
            icon_name (str): icon file name.

        Returns:
            pathlib.Path: icon file path.
        """
        return cls.icons_directory() / icon_name

    @classmethod
    @abstractmethod
    def initialize(cls) -> typing.Self:
        """Create the plugin instance. Subclasses must implement.

        Returns:
            typing.Self: initialized plugin.
        """
        raise NotImplementedError(f"{cls.__name__} must implement initialize()")

    @classmethod
    def get_type_id(cls) -> str:
        """str: unique plugin id."""
        return ""

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return cls.get_type_id()

    @classmethod
    def get_palette_name(cls) -> str:
        """str: name of the palette section holding the types of the plugin."""
        return cls.get_type_display_name()

    @classmethod
    def get_tags(cls) -> set[str]:
        """set[str]: plugin tags."""
        return set()
