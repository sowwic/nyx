import logging


from nyx.api.v1 import Stage, Link, CoreNodes, commands


LOGGER = logging.getLogger(__name__)


def test_unlink_single_push():
    """Test creating a node with default parameters."""
    stage = Stage()
    node1_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.ACTION)
    node2_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.ACTION)

    stage.push_command(node1_command)
    stage.push_command(node2_command)

    # TODO: Replace with link command because lshift has not use_uuid param
    link = node1_command.result_node["flow"] >> node2_command.result_node["flow"]
    assert Link.is_registered(stage, link)

    unlink_command = commands.UnlinkNodeComponentsCommand(
        stage=stage, link_uuid=link.uuid
    )
    stage.push_command(unlink_command)
    assert not Link.is_registered(stage, link)


def test_unlink_undo_redo():
    """Test creating a node with default parameters."""
    stage = Stage()
    node1_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.ACTION)
    node2_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.ACTION)

    stage.push_command(node1_command)
    stage.push_command(node2_command)

    # TODO: Replace with link command because lshift has not use_uuid param
    link = node1_command.result_node["flow"] >> node2_command.result_node["flow"]
    assert Link.is_registered(stage, link)

    unlink_command = commands.UnlinkNodeComponentsCommand(
        stage=stage, link_uuid=link.uuid
    )
    stage.push_command(unlink_command)

    stage.undo_stack.undo()
    assert Link.is_registered(stage, link)

    stage.undo_stack.redo()
    assert not Link.is_registered(stage, link)


def test_unlink_undo_redo_with_parent():
    """Test creating a node with default parameters."""
    stage = Stage()
    node1_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.ACTION)
    node2_command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.ACTION)

    stage.push_command(node1_command)
    stage.push_command(node2_command)

    link_command = commands.LinkNodeComponentsCommand(
        stage=stage,
        source=node1_command.result_node["flow"],
        target=node2_command.result_node["flow"],
    )
    stage.push_command(link_command)
    assert Link.is_registered(stage, link_command.result_link_uuid) is True

    unlink_command = commands.UnlinkNodeComponentsCommand(
        stage=stage, link_uuid=link_command.result_link.uuid
    )
    stage.push_command(unlink_command)
    assert Link.is_registered(stage, link_command.result_link_uuid) is False

    stage.undo_stack.undo()
    assert Link.is_registered(stage, link_command.result_link_uuid) is True
    stage.undo_stack.undo()
    stage.undo_stack.undo()

    stage.undo_stack.redo()
    stage.undo_stack.redo()

    assert Link.is_registered(stage, link_command.result_link_uuid) is True

    stage.undo_stack.redo()

    assert Link.is_registered(stage, link_command.result_link_uuid) is False
