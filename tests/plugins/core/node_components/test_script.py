import typing
import pytest

from nyx.api.v1 import Stage, commands, CoreNodes, CoreNodeComponents

if typing.TYPE_CHECKING:
    from nyx.plugins.core.nodes.action import ActionNode


def test_script_uses_node_ref(make_script: typing.Callable):
    """Test ScriptComponent execution of script from path.

    Args:
        importable_module: fixture function for module creation.
        request: pytest request node
    """
    test_value_cpnt_name = "test_value"
    test_expected_value = 1

    test_script = make_script(
        f'nyx_node["{test_value_cpnt_name}"].push_value({test_expected_value})'
    )
    stage = Stage()

    node_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.ACTION)
    stage.push_command(node_command)
    node: ActionNode = stage.get_object(node_command.result_node.uuid)
    script_cpnt_command = commands.AddNodeComponentCommand(
        node=node, type_id=CoreNodeComponents.SCRIPT, name="test_script"
    )
    value_cpnt_command = commands.AddNodeComponentCommand(
        node=node, type_id=CoreNodeComponents.VALUE, name=test_value_cpnt_name
    )

    stage.push_command(value_cpnt_command)
    stage.push_command(script_cpnt_command)

    node["test_script"].push_value(str(test_script))
    assert node[test_value_cpnt_name].pull_value() != test_expected_value
    stage.crawler.start(start_node=node)
    assert node[test_value_cpnt_name].pull_value() == test_expected_value


def test_script_raises(make_script: typing.Callable, request: pytest.FixtureRequest):
    """Test that error in node execution propagates.

    Args:
        make_script: fixture function for temp script creation
        request: pytest request node
    """
    test_script = make_script(f'raise RuntimeError("{request.node.name}")')
    stage = Stage()

    node_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.ACTION)
    stage.push_command(node_command)
    node: ActionNode = stage.get_object(node_command.result_node.uuid)

    script_cpnt_command = commands.AddNodeComponentCommand(
        node=node, type_id=CoreNodeComponents.SCRIPT, name="test_script"
    )
    stage.push_command(script_cpnt_command)

    node["test_script"].push_value(str(test_script))

    with pytest.raises(RuntimeError, match=request.node.name) as err:
        stage.crawler.start(start_node=node)
        assert node.raised_exception == err


def test_module_uses_node_ref(
    importable_module: typing.Callable, request: pytest.FixtureRequest
):
    """Test ScriptComponent execution of module.path:entry_point

    Args:
        importable_module: fixture function for module creation.
        request: pytest request node
    """
    # Test values
    test_value_cpnt_name = "test_value"
    test_expected_value = 1
    entry_point_name = "entry_point"

    module_content = (
        f"def {entry_point_name}():\n    "
        f"nyx_node['{test_value_cpnt_name}'].push_value({test_expected_value})\n"
    )
    module_name = importable_module(
        f"fixture_module_{request.node.name}", module_content
    )

    # Stage setup
    stage = Stage()
    node_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.ACTION)
    stage.push_command(node_command)
    node: ActionNode = stage.get_object(node_command.result_node.uuid)
    script_cpnt_command = commands.AddNodeComponentCommand(
        node=node, type_id=CoreNodeComponents.SCRIPT, name="test_script"
    )
    value_cpnt_command = commands.AddNodeComponentCommand(
        node=node, type_id=CoreNodeComponents.VALUE, name=test_value_cpnt_name
    )

    stage.push_command(value_cpnt_command)
    stage.push_command(script_cpnt_command)

    # Assign component value and execute
    node["test_script"].push_value(str(f"{module_name}:{entry_point_name}"))
    assert node[test_value_cpnt_name].pull_value() != test_expected_value
    stage.crawler.start(start_node=node)
    assert node[test_value_cpnt_name].pull_value() == test_expected_value
