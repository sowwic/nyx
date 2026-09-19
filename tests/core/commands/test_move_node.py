import logging

from PySide6.QtCore import QPointF

from nyx.core.commands import CreateNodeCommand, MoveNodeCommand
from nyx.core.stage import Stage

LOGGER = logging.getLogger(__name__)


def test_move_single_node(nyx_app) -> None:
    """Test moving a single node.

    Args:
        nyx_app (NyxApplication): application fixture
    """
    stage = Stage()
    test_node_path = stage.root_node.path / "node"
    stage.push_command(CreateNodeCommand(stage=stage))
    node = stage.node(test_node_path)

    new_position = QPointF(10.0, 10.0)
    assert node.position() != new_position

    command = MoveNodeCommand(stage=stage, nodes=[node], new_positions=[new_position])
    stage.push_command(command)
    assert node.position() == new_position


def test_move_multiple_nodes(nyx_app) -> None:
    """Test moving multiple nodes.

    Args:
        nyx_app (NyxApplication): application fixture
    """
    stage = Stage()
    stage.push_command(CreateNodeCommand(stage=stage, node_name="node_1"))
    stage.push_command(CreateNodeCommand(stage=stage, node_name="node_2"))
    stage.push_command(CreateNodeCommand(stage=stage, node_name="node_3"))

    node1 = stage.node(stage.root_node.path / "node_1")
    node2 = stage.node(stage.root_node.path / "node_2")
    node3 = stage.node(stage.root_node.path / "node_3")

    new_position1 = QPointF(10.0, 10.0)
    new_position2 = QPointF(5.0, 25.0)
    new_position3 = QPointF(100.0, 20.0)

    assert node1.position() != new_position1
    assert node2.position() != new_position2
    assert node3.position() != new_position3

    command = MoveNodeCommand(
        stage=stage,
        nodes=[node1, node2, node3],
        new_positions=[new_position1, new_position2, new_position3],
    )
    stage.push_command(command)
    assert node1.position() == new_position1
    assert node2.position() == new_position2
    assert node3.position() == new_position3


def test_move_multiple_nodes_undo_redo(nyx_app) -> None:
    """Test moving nodes undo-redo.

    Args:
        nyx_app (NyxApplication): application fixture
    """

    def assert_nodes_have_original_position():
        assert node1.position() != new_position1
        assert node2.position() != new_position2
        assert node3.position() != new_position3

    def assert_nodes_have_updated_position():
        assert node1.position() == new_position1
        assert node2.position() == new_position2
        assert node3.position() == new_position3

    stage = Stage()
    stage.push_command(CreateNodeCommand(stage=stage, node_name="node_1"))
    stage.push_command(CreateNodeCommand(stage=stage, node_name="node_2"))
    stage.push_command(CreateNodeCommand(stage=stage, node_name="node_3"))

    node1 = stage.node(stage.root_node.path / "node_1")
    node2 = stage.node(stage.root_node.path / "node_2")
    node3 = stage.node(stage.root_node.path / "node_3")

    new_position1 = QPointF(10.0, 10.0)
    new_position2 = QPointF(5.0, 25.0)
    new_position3 = QPointF(100.0, 20.0)

    command = MoveNodeCommand(
        stage=stage,
        nodes=[node1, node2, node3],
        new_positions=[new_position1, new_position2, new_position3],
    )

    stage.push_command(command)
    assert_nodes_have_updated_position()
    stage.undo_stack.undo()
    assert_nodes_have_original_position()
    stage.undo_stack.redo()
    assert_nodes_have_updated_position()
