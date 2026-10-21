import pytest

from nyx.api.v1 import CoreDatatypes, CoreNodes, NYX_REGISTRY, Stage, commands
from nyx.core.plugin_subsystem.plugin import NyxPluginContents
from nyx.core.function_node import FunctionNode


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
def register(monkeypatch):
    """Register function nodes in the registry for the test."""
    monkeypatch.setattr(NYX_REGISTRY, "nodes", NYX_REGISTRY.nodes.copy())
    contents = NyxPluginContents()

    def _register(func, **kwargs):
        node_cls = contents.register_function_node(func, **kwargs)
        NYX_REGISTRY.nodes[node_cls.get_type_id()] = node_cls
        return node_cls

    _register.contents = contents
    return _register


def make_node(stage, type_id, name=None):
    command = commands.CreateNodeCommand(stage=stage, type_id=type_id, name=name)
    stage.push_command(command)
    return command.result_node


def test_node_type_is_described_by_the_function(register):
    node_cls = register(add)

    assert issubclass(node_cls, FunctionNode)
    assert node_cls.get_type_id() == f"function:{__name__}.add"
    assert node_cls.get_type_display_name() == "Add"
    assert node_cls.DEFAULT_NAME == "add"
    assert node_cls.get_type_icon() == ":/icons/function"
    assert "function" in node_cls.get_tags()
    assert node_cls in register.contents.nodes


def test_display_name_is_the_capitalized_words_of_the_function_name(register):
    def is_equal_to(a, b):
        return a == b

    node_cls = register(is_equal_to)

    assert node_cls.get_type_display_name() == "Is Equal To"
    assert node_cls.DEFAULT_NAME == "is_equal_to"


def test_components_follow_the_signature(register):
    node = make_node(Stage(), register(add).get_type_id())

    assert node["flow"].readable and node["flow"].writable
    for name in ("a", "b"):
        assert node[name].writable and not node[name].readable
        assert node[name].datatype_id == CoreDatatypes.INT
    assert node["a"].raw_value == 0
    assert node["b"].raw_value == 2
    assert node["return"].readable and not node["return"].writable
    assert node["return"].datatype_id == CoreDatatypes.INT


def test_datatypes_fall_back_to_object(register):
    node = make_node(Stage(), register(describe).get_type_id())

    assert node["text"].datatype_id == CoreDatatypes.STRING  # str | None
    assert node["thing"].datatype_id == CoreDatatypes.OBJECT  # no hint
    assert node["ratio"].datatype_id == CoreDatatypes.FLOAT
    assert node["return"].datatype_id == CoreDatatypes.OBJECT  # no hint


def test_unknown_class_hint_is_object(register):
    node = make_node(Stage(), register(custom).get_type_id())

    assert node["value"].datatype_id == CoreDatatypes.OBJECT
    assert node["return"].datatype_id == CoreDatatypes.OBJECT


def test_function_runs_when_the_flow_reaches_the_node(register):
    stage = Stage()
    start = make_node(stage, CoreNodes.FLOW_START, name="start")
    node = make_node(stage, register(add).get_type_id(), name="add")
    start["flow"] >> node["flow"]
    node["a"].push_value(40)

    stage.crawler.start()

    assert node["return"].pull_value() == 42


def test_linked_value_is_passed_as_argument(register):
    stage = Stage()
    start = make_node(stage, CoreNodes.FLOW_START, name="start")
    first = make_node(stage, register(add).get_type_id(), name="first")
    second = make_node(stage, register(describe).get_type_id(), name="second")
    start["flow"] >> first["flow"]
    first["flow"] >> second["flow"]
    first["a"].push_value(1)
    first["return"] >> second["thing"]

    stage.crawler.start()

    assert second["return"].pull_value() == ":3:0.5"  # text keeps its datatype default


def test_exception_of_the_function_fails_the_execution(register):
    stage = Stage()
    start = make_node(stage, CoreNodes.FLOW_START, name="start")
    node = make_node(stage, register(fail).get_type_id(), name="fail")
    start["flow"] >> node["flow"]

    with pytest.raises(RuntimeError, match="boom"):
        stage.crawler.start()


def test_custom_type_id(register):
    assert register(add, type_id="test:add").get_type_id() == "test:add"


def test_duplicate_and_invalid_functions_are_rejected(register):
    register(add)
    with pytest.raises(ValueError):
        register.contents.register_function_node(add)
    with pytest.raises(TypeError):
        register.contents.register_function_node(lambda value: value)
    with pytest.raises(TypeError):
        register.contents.register_function_node("not callable")


def test_var_arguments_get_no_components(register):
    def variadic(a: int, *args, **kwargs) -> int:
        return a

    node = make_node(Stage(), register(variadic).get_type_id())

    assert node["a"] is not None
    for name in ("args", "kwargs"):
        with pytest.raises(ValueError, match="no component"):
            node[name]


def test_string_result_is_not_evaluated_as_an_expression(register):
    def number_text(value: int) -> str:
        return str(value)

    stage = Stage()
    start = make_node(stage, CoreNodes.FLOW_START, name="start")
    node = make_node(stage, register(number_text).get_type_id(), name="text")
    start["flow"] >> node["flow"]
    node["value"].push_value(5)

    stage.crawler.start()

    assert node["return"].pull_value() == "5"
