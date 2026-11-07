import typing
from nyx.api.v1 import Stage, CoreNodes, commands

if typing.TYPE_CHECKING:
    from nyx.stdlib.nodes.dictionary import DictionaryNode


def test_dictionary_result_pulls_a_dict_and_displays_text():
    """The pulled result is a dict, the display value a string the UI can show."""
    stage = Stage()
    command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.DICT)
    stage.push_command(command)
    dict_node: DictionaryNode = command.result_node

    value_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.VALUE)
    stage.push_command(value_command)
    value_command.result_node["value"].push_value(5)

    result = dict_node["result"]
    assert isinstance(result.pull_value(), dict)
    assert isinstance(result.get_display_value(), str)
    assert result.get_display_value() == str(result.pull_value())
