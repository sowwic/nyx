import typing
from nyx.api.v1 import Stage, CoreNodes, CoreNodeComponents, commands

if typing.TYPE_CHECKING:
    from nyx.stdlib.nodes.list_node import ListNode


def _create_list_node(stage: Stage) -> ListNode:
    command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.LIST)
    stage.push_command(command)
    return command.result_node


def test_list_result_collects_values_in_order_and_displays_text():
    stage = Stage()
    list_node = _create_list_node(stage)
    for each_value in (1, 2, 3):
        value_cpnt = list_node.components_model.create_component(
            CoreNodeComponents.VALUE
        )
        list_node.components_model.add_component(value_cpnt)
        value_cpnt.push_value(each_value)

    result = list_node["result"]
    assert result.pull_value() == [1, 2, 3]
    assert result.get_display_value() == "[1, 2, 3]"


def test_list_result_includes_values_of_source_nodes():
    stage = Stage()
    value_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.VALUE)
    stage.push_command(value_command)
    value_command.result_node["value"].push_value(7)

    list_node = _create_list_node(stage)
    path_cpnt = list_node.components_model.create_component(
        CoreNodeComponents.STAGE_OBJECT_PATH
    )
    list_node.components_model.add_component(path_cpnt)
    path_cpnt.push_value(value_command.result_node.path.as_posix())

    assert list_node["result"].pull_value() == [7]


def test_list_result_is_hidden_from_the_inspector():
    stage = Stage()
    assert _create_list_node(stage)["result"].inspector_hidden is True
