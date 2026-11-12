"""Helpers shared by the tests that build stages."""

from nyx.api.v1 import CoreNodes, Stage, commands

# Commands hold their stage weakly, so stages made inside helpers are kept here until
# the end of the test (see `keep_stages_alive` in conftest.py).
STAGES: list[Stage] = []


def create_node(stage, type_id=CoreNodes.EMPTY, name=None, parent=None):
    """Create a node through a command.

    Args:
        stage (Stage): stage to create the node in.
        type_id (str): type id of the node.
        name (str | None): node name.
        parent (Node | None): parent node, the stage root by default.

    Returns:
        Node: the new node.
    """
    STAGES.append(stage)
    command = commands.CreateNodeCommand(
        stage=stage, type_id=type_id, name=name, parent_node=parent
    )
    stage.push_command(command)
    return command.result_node
