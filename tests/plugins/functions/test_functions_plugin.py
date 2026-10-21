import pytest

from nyx.api.v1 import CoreDatatypes, CoreNodes, NYX_REGISTRY, Stage, commands


pytestmark = pytest.mark.with_plugins("NyxCore", "NyxFunctions")


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
    ):
        assert NYX_REGISTRY.get_node_cls(type_id) is not None

    from nyx.plugins.functions import logic_operations, math_operations
    from nyx.core.function_node import find_public_functions

    expected = len(find_public_functions(math_operations)) + len(
        find_public_functions(logic_operations)
    )
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
