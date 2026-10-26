import importlib

import pytest

from nyx.api.v1 import CoreDatatypes, CoreNodes, NYX_REGISTRY, Stage, commands


pytestmark = pytest.mark.with_plugins(
    "NyxStdlib",
    "NyxMathFunctions",
    "NyxLogicFunctions",
    "NyxStringFunctions",
    "NyxListFunctions",
    "NyxDictionaryFunctions",
    "NyxJSONFunctions",
    "NyxFileFunctions",
    "NyxSystemFunctions",
    "NyxDateTimeFunctions",
    "NyxRandomFunctions",
    "NyxPathFunctions",
    "NyxRegexFunctions",
    "NyxEncodingFunctions",
)

FUNCTION_GROUPS = (
    "math",
    "logic",
    "string",
    "list",
    "dict",
    "json",
    "file",
    "system",
    "datetime",
    "random",
    "path",
    "regex",
    "encoding",
)


def make_node(stage, type_id, name=None):
    command = commands.CreateNodeCommand(stage=stage, type_id=type_id, name=name)
    stage.push_command(command)
    return command.result_node


def test_plugin_registers_a_node_for_every_operation():
    for type_id in (
        "function:math.add",
        "function:math.clamp",
        "function:logic.is_instance",
        "function:logic.is_equal",
        "function:string.split",
        "function:list.sort",
        "function:dict.merge",
        "function:json.parse_json",
        "function:file.read_text",
        "function:system.get_env",
        "function:datetime.format_datetime",
        "function:random.random_int",
        "function:path.join_path",
        "function:regex.find_all",
        "function:encoding.sha256",
    ):
        assert NYX_REGISTRY.get_node_cls(type_id) is not None

    from nyx.core.function_node import find_public_functions

    expected = 0
    for group in FUNCTION_GROUPS:
        module = importlib.import_module(
            f"nyx.plugins.functions.{group}_operations.operations"
        )
        expected += len(find_public_functions(module))
    registered = [
        type_id for type_id in NYX_REGISTRY.nodes if type_id.startswith("function:")
    ]
    assert len(registered) == expected


def test_math_node_has_typed_components():
    node = make_node(Stage(), "function:math.clamp")

    assert node["value"].datatype_id == CoreDatatypes.FLOAT
    assert node["high"].raw_value == 1.0
    assert node["return"].datatype_id == CoreDatatypes.FLOAT


def test_logic_node_returns_a_bool():
    node = make_node(Stage(), "function:logic.is_equal")

    assert node["a"].datatype_id == CoreDatatypes.OBJECT
    assert node["return"].datatype_id == CoreDatatypes.BOOL


def test_nodes_run_in_a_flow():
    stage = Stage()
    start = make_node(stage, CoreNodes.FLOW_START, name="start")
    add = make_node(stage, "function:math.add", name="add")
    check = make_node(stage, "function:logic.is_equal", name="check")
    start["flow"] >> add["flow"]
    add["flow"] >> check["flow"]
    add["a"].push_value(2)
    add["b"].push_value(3)
    add["return"] >> check["a"]
    check["b"].push_value(5)

    stage.crawler.start()

    assert add["return"].pull_value() == 5
    assert check["return"].pull_value() is True


def test_every_plugin_has_a_palette_name():
    names = {
        "NyxStdlib": "Core",
        "NyxMathFunctions": "Math Operations",
        "NyxListFunctions": "List Operations",
        "NyxDictionaryFunctions": "Dictionary Operations",
        "NyxJSONFunctions": "JSON Operations",
    }
    for type_id, name in names.items():
        assert NYX_REGISTRY.plugins[type_id].plugin_cls.get_palette_name() == name


def test_nodes_know_the_palette_section_of_their_plugin():
    assert NYX_REGISTRY.get_node_cls(
        "function:list.sort"
    ).get_source_plugin_palette_name() == ("List Operations")
    assert NYX_REGISTRY.nodes["core:branch"].get_source_plugin_palette_name() == "Core"


def test_same_function_name_in_different_plugins_does_not_conflict():
    assert NYX_REGISTRY.get_node_cls("function:string.length") is not None
    assert NYX_REGISTRY.get_node_cls("function:list.length") is not None
    assert NYX_REGISTRY.get_node_cls("function:dict.length") is not None


def test_return_is_not_editable_but_parameters_are():
    node = make_node(Stage(), "function:math.clamp")

    assert node["return"].is_editable is False
    assert node["value"].is_editable is True


def test_function_nodes_are_tagged_with_their_operation_type():
    for group in FUNCTION_GROUPS:
        module = importlib.import_module(
            f"nyx.plugins.functions.{group}_operations.operations"
        )
        from nyx.core.function_node import find_public_functions

        for function in find_public_functions(module):
            node_cls = NYX_REGISTRY.get_node_cls(f"function:{group}.{function.__name__}")
            assert node_cls.get_tags() == {"function", group}
