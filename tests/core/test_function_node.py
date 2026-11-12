import pytest

from nyx.api.v1 import CoreDatatypes, CoreNodes, NYX_REGISTRY, Stage, commands
from nyx.core.plugin_subsystem.plugin import NyxPluginContents
from nyx.core.function_node import FunctionNode
from stage_helpers import create_node


def add(a: int, b: int = 2) -> int:
    """Add two numbers."""
    return a + b


def describe(text: str | None, thing, ratio: float = 0.5):
    return f"{text}:{thing}:{ratio}"


def fail(value: int) -> int:
    raise RuntimeError("boom")


class Custom:
    pass


def custom(value: Custom) -> Custom:
    return value


@pytest.fixture
def register_function(monkeypatch):
    """Register function nodes in the registry for the test."""
    monkeypatch.setattr(NYX_REGISTRY, "nodes", NYX_REGISTRY.nodes.copy())
    contents = NyxPluginContents()

    def _register(func, **kwargs):
        node_cls = contents.register_function_node(func, **kwargs)
        NYX_REGISTRY.nodes[node_cls.get_type_id()] = node_cls
        return node_cls

    _register.contents = contents
    return _register


def test_node_type_is_described_by_the_function(register_function):
    node_cls = register_function(add)

    assert issubclass(node_cls, FunctionNode)
    assert node_cls.get_type_id() == f"function:{__name__}.add"
    assert node_cls.get_type_display_name() == "Add"
    assert node_cls.DEFAULT_NAME == "add"
    assert node_cls.get_type_icon() == ":/icons/function"
    assert "function" in node_cls.get_tags()
    assert node_cls in register_function.contents.nodes


def test_display_name_is_the_capitalized_words_of_the_function_name(register_function):
    def is_equal_to(a, b):
        return a == b

    node_cls = register_function(is_equal_to)

    assert node_cls.get_type_display_name() == "Is Equal To"
    assert node_cls.DEFAULT_NAME == "is_equal_to"


def test_components_follow_the_signature(register_function):
    node = create_node(Stage(), register_function(add).get_type_id())

    assert node["flow"].readable and node["flow"].writable
    for name in ("a", "b"):
        assert node[name].writable and not node[name].readable
        assert node[name].datatype_id == CoreDatatypes.INT
    assert node["a"].raw_value == 0
    assert node["b"].raw_value == 2
    assert node["return"].readable and not node["return"].writable
    assert node["return"].datatype_id == CoreDatatypes.INT


def test_datatypes_fall_back_to_object(register_function):
    node = create_node(Stage(), register_function(describe).get_type_id())

    assert node["text"].datatype_id == CoreDatatypes.STRING  # str | None
    assert node["thing"].datatype_id == CoreDatatypes.OBJECT  # no hint
    assert node["ratio"].datatype_id == CoreDatatypes.FLOAT
    assert node["return"].datatype_id == CoreDatatypes.OBJECT  # no hint


def test_unknown_class_hint_is_object(register_function):
    node = create_node(Stage(), register_function(custom).get_type_id())

    assert node["value"].datatype_id == CoreDatatypes.OBJECT
    assert node["return"].datatype_id == CoreDatatypes.OBJECT


def test_function_runs_when_the_flow_reaches_the_node(register_function):
    stage = Stage()
    start = create_node(stage, CoreNodes.FLOW_START, name="start")
    node = create_node(stage, register_function(add).get_type_id(), name="add")
    start["flow"] >> node["flow"]
    node["a"].push_value(40)

    stage.crawler.start()

    assert node["return"].pull_value() == 42


def test_linked_value_is_passed_as_argument(register_function):
    stage = Stage()
    start = create_node(stage, CoreNodes.FLOW_START, name="start")
    first = create_node(stage, register_function(add).get_type_id(), name="first")
    second = create_node(stage, register_function(describe).get_type_id(), name="second")
    start["flow"] >> first["flow"]
    first["flow"] >> second["flow"]
    first["a"].push_value(1)
    first["return"] >> second["thing"]

    stage.crawler.start()

    assert second["return"].pull_value() == ":3:0.5"  # text keeps its datatype default


def test_exception_of_the_function_fails_the_execution(register_function):
    stage = Stage()
    start = create_node(stage, CoreNodes.FLOW_START, name="start")
    node = create_node(stage, register_function(fail).get_type_id(), name="fail")
    start["flow"] >> node["flow"]

    with pytest.raises(RuntimeError, match="boom"):
        stage.crawler.start()


def test_custom_type_id(register_function):
    assert register_function(add, type_id="test:add").get_type_id() == "test:add"


def test_duplicate_and_invalid_functions_are_rejected(register_function):
    register_function(add)
    with pytest.raises(ValueError):
        register_function.contents.register_function_node(add)
    with pytest.raises(TypeError):
        register_function.contents.register_function_node(lambda value: value)
    with pytest.raises(TypeError):
        register_function.contents.register_function_node("not callable")


def test_var_arguments_get_no_components(register_function):
    def variadic(a: int, *args, **kwargs) -> int:
        return a

    stage = Stage()
    node = create_node(stage, register_function(variadic).get_type_id())

    assert node["a"] is not None
    for name in ("args", "kwargs"):
        with pytest.raises(ValueError, match="no component"):
            node[name]


def test_string_result_is_not_evaluated_as_an_expression(register_function):
    def number_text(value: int) -> str:
        return str(value)

    stage = Stage()
    start = create_node(stage, CoreNodes.FLOW_START, name="start")
    node = create_node(stage, register_function(number_text).get_type_id(), name="text")
    start["flow"] >> node["flow"]
    node["value"].push_value(5)

    stage.crawler.start()

    assert node["return"].pull_value() == "5"


def test_collection_hints_give_list_and_dict_datatypes(register_function):
    import typing

    def collect(
        items: list,
        typed_items: list[int],
        mapping: dict,
        typed_mapping: dict[str, int],
        legacy: typing.Dict[str, int],  # noqa: UP006
        maybe: typing.Optional[list[str]] = None,  # noqa: UP045
    ) -> list[str]:
        return [str(len(items))]

    node = create_node(Stage(), register_function(collect).get_type_id())

    for name in ("items", "typed_items", "maybe"):
        assert node[name].datatype_id == CoreDatatypes.LIST
    for name in ("mapping", "typed_mapping", "legacy"):
        assert node[name].datatype_id == CoreDatatypes.DICT
    assert node["return"].datatype_id == CoreDatatypes.LIST


def test_function_with_a_list_and_a_dict_runs(register_function):
    def lookup(keys: list, table: dict) -> list:
        return [table[key] for key in keys]

    stage = Stage()
    start = create_node(stage, CoreNodes.FLOW_START, name="start")
    node = create_node(stage, register_function(lookup).get_type_id(), name="lookup")
    start["flow"] >> node["flow"]
    node["keys"].push_value(["a", "b"])
    node["table"].push_value({"a": 1, "b": 2})

    stage.crawler.start()

    assert node["return"].pull_value() == [1, 2]


def test_display_survives_a_link_from_a_getter_pointing_at_nothing():
    from nyx.api.v1 import CoreNodes, Stage

    stage = Stage()

    def make(type_id, name):
        command = commands.CreateNodeCommand(stage=stage, type_id=type_id, name=name)
        stage.push_command(command)
        return command.result_node

    getter = make(CoreNodes.GET, "get")
    cast = make(CoreNodes.TYPE_CAST, "cast")
    getter["value"] >> cast["type"]

    # Pulling the value fails, drawing the node and its tooltip must not
    assert cast["type"].get_display_value() is not None
    assert isinstance(cast.subtitle, str)


def test_parse_docstring_reads_args_and_returns():
    from nyx.core.function_node import parse_docstring

    arguments, returns = parse_docstring(
        """Do a thing.

        Longer text.

        Args:
            text (str): The text
                that wraps.
            count: How many.

        Returns:
            str: The result.
        """
    )

    assert arguments == {"text": "The text that wraps.", "count": "How many."}
    assert returns == "The result."


def test_parse_docstring_without_sections():
    from nyx.core.function_node import parse_docstring

    assert parse_docstring("Add two numbers.") == ({}, "Add two numbers.")
    assert parse_docstring(None) == ({}, "")


def test_function_node_components_get_descriptions_from_the_docstring():
    from nyx.api.v1 import Stage
    from nyx.core.function_node import create_function_node_class
    from nyx.api.v1 import NYX_REGISTRY

    def shout(text: str, times: int = 2, plain: str = "") -> str:
        """Repeat a text loudly.

        Args:
            text: Text to shout.
            times: How often.

        Returns:
            The shouted text.
        """
        return text * times

    node_cls = create_function_node_class(shout, type_id="function:test.shout")
    NYX_REGISTRY.nodes["function:test.shout"] = node_cls
    try:
        stage = Stage()
        command = commands.CreateNodeCommand(stage=stage, type_id="function:test.shout")
        stage.push_command(command)
        node = command.result_node
    finally:
        del NYX_REGISTRY.nodes["function:test.shout"]

    assert node["text"].description == "Text to shout."
    assert node["times"].description == "How often."
    # Not documented: the one of the component type
    assert node["plain"].description == type(node["plain"]).get_description() or (
        node["plain"].description == type(node["plain"]).get_type_display_name()
    )
    assert node["return"].description == "The shouted text."
