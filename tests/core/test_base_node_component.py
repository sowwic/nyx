import pytest

from nyx.core import Node, Stage
from nyx.core.node_component._base_component import NodeComponent, EMPTY_LINKS_DICT


def test_init_base_component():
    cpnt = NodeComponent()
    cpnt.name == NodeComponent.DEFAULT_NAME
    cpnt.is_active is True
    cpnt.is_readable is False
    cpnt.is_writable is False
    cpnt.links == EMPTY_LINKS_DICT


def test_add_base_component_to_node():
    stage = Stage()
    node = Node("test")
    component = NodeComponent()
    node.add_component(component)
    stage.add_node(node)

    assert component.as_path() == node.cached_path.with_suffix(f".{component.name}")

def test_component_name_indexing():
    stage = Stage()
    node = Node("test")
    stage.add_node(node)

    test_name = "test"
    component1 = NodeComponent(name=test_name)
    component2 = NodeComponent(name=test_name)

    node.add_component(component1)
    node.add_component(component2)

    assert len(node.components_model.list_components()) == 2
    assert component1.name == test_name
    assert component2.name == test_name + "1"
