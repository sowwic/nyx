import logging

from nyx.api.v1 import (
    Node,
    Stage,
    CoreNodes,
    NodeExecutionStatus,
    commands,
)
from nyx.core.protocols.registry_entry import IRegistryEntry

LOGGER = logging.getLogger(__name__)


def test_add_node_to_root():
    stage = Stage()

    create_node_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.EMPTY
    )
    stage.push_command(create_node_command)
    node = create_node_command.result_node

    stage.add_node(node)

    assert isinstance(node, IRegistryEntry)
    assert stage.root_node.hasChildren()
    assert stage.root_node.child(0) is node


def test_add_node_with_parent():
    stage = Stage()
    create_parent_node_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.EMPTY
    )
    stage.push_command(create_parent_node_command)
    parent_node = create_parent_node_command.result_node

    child_node1_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.EMPTY, parent_node=parent_node
    )
    child_node2_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.EMPTY, parent_node=parent_node
    )
    stage.push_command(child_node1_command, child_node2_command)

    child_node1 = child_node1_command.result_node
    child_node2 = child_node2_command.result_node

    assert [child_node1, child_node2] == parent_node.list_children()
    assert [parent_node] == child_node1.list_parents()
    assert [parent_node] == child_node2.list_parents()


def test_node_execute_while_active():
    stage = Stage()
    create_node_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.EMPTY
    )
    stage.push_command(create_node_command)
    node = create_node_command.result_node

    node.execution_hook()

    assert node.is_active()
    assert node.execution_status is NodeExecutionStatus.SUCCESS


def test_node_execute_while_not_active():
    stage = Stage()
    create_node_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.EMPTY
    )
    stage.push_command(create_node_command)
    node = create_node_command.result_node

    node.set_active(False)
    node.execution_hook()

    assert not node.is_active()
    assert node.execution_status is NodeExecutionStatus.NOT_RAN


def test_node_list_children_tree():
    stage = Stage()
    create_node_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.EMPTY
    )
    stage.push_command(create_node_command)
    node = create_node_command.result_node

    parent_node = node
    added_nodes = []
    for _ in range(5):
        create_child_node_command = commands.CreateNodeCommand(
            stage=stage, type_id=CoreNodes.EMPTY, parent_node=parent_node
        )
        stage.push_command(create_child_node_command)
        parent_node = create_child_node_command.result_node
        added_nodes.append(parent_node)

    assert node.list_children_tree() == added_nodes


def test_deleting_parent_node_removes_childrens_uuids():
    stage = Stage()
    create_node_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.EMPTY
    )
    stage.push_command(create_node_command)
    node = create_node_command.result_node

    parent_node = node
    uuids = [node.uuid]

    for _ in range(5):
        create_child_node_command = commands.CreateNodeCommand(
            stage=stage, type_id=CoreNodes.EMPTY, parent_node=parent_node
        )
        stage.push_command(create_child_node_command)
        parent_node = create_child_node_command.result_node
        uuids.append(parent_node.uuid)
    LOGGER.debug(f"UUIDS map: {stage.uuid_map}")

    node.delete()
    LOGGER.debug(f"Path map after deletion: {stage.uuid_map}")

    assert len(stage.uuid_map) == 1
    assert stage.node_from_path(stage.root_node.path) is not None


def test_find_flow_start_node():
    stage = Stage()
    parent_create_command = commands.CreateNodeCommand(stage=stage)
    stage.push_command(parent_create_command)
    flow_start_create_command = commands.CreateNodeCommand(
        stage=stage,
        type_id=CoreNodes.FLOW_START,
        parent_node=parent_create_command.result_node,
    )
    stage.push_command(flow_start_create_command)
    parent_node = stage.get_object(parent_create_command.result_node.uuid)

    flow_start_node: Node = parent_node.find_flow_start_node()
    assert flow_start_node is not None
    assert flow_start_node.get_type_id() == CoreNodes.FLOW_START


def test_setup_components_marked_as_builtin():
    stage = Stage()
    create_node_command = commands.CreateNodeCommand(
        stage=stage, type_id=CoreNodes.SEQUENCE
    )
    stage.push_command(create_node_command)
    test_node = create_node_command.result_node
    for each_component in test_node.components_model.list_components():
        assert each_component.is_built_in is True
