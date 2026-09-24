import typing
import pytest

from nyx.api.v1 import Stage, commands, CoreNodes, CoreNodeComponents

if typing.TYPE_CHECKING:
    from nyx.plugins.core.nodes.action import ActionNode


def test_script_uses_node_ref(make_script: typing.Callable):
    test_value_cpnt_name = "test_value"
    test_expected_value = 1

    test_script = make_script(f'nyx_node["{test_value_cpnt_name}"].value = 1')
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

    node["test_script"].value = str(test_script)
    stage.crawler.start(start_node=node)

    assert node[test_value_cpnt_name].value == test_expected_value


def test_script_raises(make_script: typing.Callable, request: pytest.FixtureRequest):
    test_script = make_script(f'raise RuntimeError("{request.node.name}")')
    stage = Stage()

    node_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.ACTION)
    stage.push_command(node_command)
    node: ActionNode = stage.get_object(node_command.result_node.uuid)

    script_cpnt_command = commands.AddNodeComponentCommand(
        node=node, type_id=CoreNodeComponents.SCRIPT, name="test_script"
    )
    stage.push_command(script_cpnt_command)

    node["test_script"].value = str(test_script)

    with pytest.raises(RuntimeError, match=request.node.name) as err:
        stage.crawler.start(start_node=node)
        assert node.raised_exception == err
