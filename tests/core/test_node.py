import logging

from nyx.api.v1 import Node, Stage, CoreNodes, CoreNodeComponents, commands
from nyx.core.protocols.registry_entry import IRegistryEntry

LOGGER = logging.getLogger(__name__)


def test_add_node_to_root():
    stage = Stage()
    node = Node("node")

    stage.add_node(node)

    assert isinstance(node, IRegistryEntry)
    assert stage.root_node.hasChildren()
    assert stage.root_node.child(0) is node


def test_add_node_with_parent():
    stage = Stage()
    parent_node = Node("node")
    stage.add_node(parent_node)

    child_node1 = Node("node", parent=parent_node)
    child_node2 = Node("node", parent=parent_node)

    assert [child_node1, child_node2] == parent_node.list_children()
    assert [parent_node] == child_node1.list_parents()
    assert [parent_node] == child_node2.list_parents()


def test_add_node_with_parent_via_stage():
    stage = Stage()
    parent_node = Node("node")
    stage.add_node(parent_node)

    child_node1 = Node("node")
    child_node2 = Node("node")

    stage.add_node([child_node1, child_node2], parent=parent_node)

    assert [child_node1, child_node2] == parent_node.list_children()
    assert [parent_node] == child_node1.list_parents()
    assert [parent_node] == child_node2.list_parents()


def test_node_delete_mid_children():
    stage = Stage()
    parent_node = Node("node")
    stage.add_node(parent_node)

    for index in range(1, 5):
        Node(parent=parent_node)

    assert len(parent_node.list_children()) == 4
    first, second, third, fourth = parent_node.list_children()
    second.delete()
    third.delete()
    assert parent_node.list_children() == [first, fourth]


def test_node_execute_while_active():
    stage = Stage()
    node = Node("node")
    stage.add_node(node)

    node.execute()

    assert node.is_active()


def test_node_execute_while_not_active():
    stage = Stage()
    node = Node("node")
    stage.add_node(node)

    node.set_active(False)

    node.execute()

    assert not node.is_active()
    # TODO add asserts for component values


def test_node_list_children_tree():
    stage = Stage()
    node = Node()
    stage.add_node(node)

    par = node

    added_nodes = []
    for _ in range(5):
        par = Node(parent=par)
        added_nodes.append(par)

    assert node.list_children_tree() == added_nodes


def test_node_rename():
    stage = Stage()
    node = Node()
    stage.add_node(node)

    # Create nested child nodes
    par = node
    for i in range(5):
        par = Node(parent=par)

    # Store old data
    children = node.list_children_tree()
    old_path = node.path
    old_child_paths = [child.path for child in children]

    # Do rename of first node
    new_name = "cool_name"
    node.rename(new_name)

    # Assertions
    assert node._cached_path == node.path
    assert old_path not in stage.path_map
    for old_child_path in old_child_paths:
        assert old_child_path not in stage.path_map

    for child in children:
        # ["/", "stage", "cool_name"]
        assert child.path.parts[2] == new_name
        assert child.path in stage.path_map


def test_node_delete_first_paths_map_valid():
    stage = Stage()
    node = Node()
    stage.add_node(node)

    par = node

    for _ in range(5):
        par = Node(parent=par)
    LOGGER.debug(f"Path map: {stage.path_map}")

    node.delete()
    LOGGER.debug(f"Path map after deletion: {stage.path_map}")

    assert len(stage.path_map) == 1
    assert stage.path_map.get(stage.root_node.path) is not None


def test_node_delete_mid_paths_map_valid():
    stage = Stage()
    node = Node()
    stage.add_node(node)

    par = node

    added_nodes = []
    for i in range(5):
        par = Node(parent=par)
        added_nodes.append(par)

    LOGGER.debug(f"Path map: {stage.path_map}")
    added_nodes[1].delete()

    LOGGER.debug(f"Path map after deletion: {stage.path_map}")

    assert stage.path_map != {}
    assert node.path in stage.path_map
    for child in node.list_children_tree():
        assert child.path in stage.path_map


def test_find_flow_start_node():
    stage = Stage()
    parent_create_command = commands.CreateNodeCommand(stage=stage)
    stage.push_command(parent_create_command)
    flow_start_create_command = commands.CreateNodeCommand(
        stage=stage,
        node_type_id=CoreNodes.FLOW_START,
        parent_path=parent_create_command.node_path,
    )
    stage.push_command(flow_start_create_command)
    parent_node = stage.node(parent_create_command.node_path)

    flow_start_node: Node = parent_node.find_flow_start_node()
    assert flow_start_node is not None
    assert flow_start_node.get_type_id() == CoreNodes.FLOW_START


def test_setup_components_marked_as_builtin():
    class TestNode(Node):
        def setup(self):
            for _ in range(3):
                flow_cpnt = self.components_model.create_component(
                    type_id=CoreNodeComponents.FLOW
                )
                value_cpnt = self.components_model.create_component(
                    type_id=CoreNodeComponents.VALUE
                )
                self.components_model.add_component(flow_cpnt)
                self.components_model.add_component(value_cpnt)

    test_node = TestNode()

    for each_component in test_node.components_model.list_components():
        assert each_component.is_built_in is True
