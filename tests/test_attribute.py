from nyx import get_main_logger, get_logger
from nyx.core import Stage
from nyx.core import Node
from nyx.core.attribute import Attribute
from nyx.utils import file_fn


LOGGER = get_main_logger()
TEST_LOGGER = get_logger(__name__)


def test_attr_getset():
    stage = Stage()
    parent_node = Node("node")
    stage.add_node(parent_node)

    node = Node("node1", parent=parent_node)
    node.add_attr("test", value=2)
    assert isinstance(node.attribs["test"], Attribute)
    assert node["test"].value == 2
    assert node["test"].cached_value is None


def test_attr_push():
    stage = Stage()
    node = Node()
    stage.add_node(node)

    node.add_attr("test")
    node["test"].push(5)

    assert node["test"].get(raw=True) is None
    assert node["test"].get(resolved=True) is None
    assert node["test"].get() == 5


def test_attr_cache_current_value():
    stage = Stage()
    node = Node()
    stage.add_node(node)

    node.add_attr("test", value=10, resolve=True)
    assert not node["test"].is_cached()
    node["test"].cache_current_value()
    assert node["test"].is_cached()


def test_attr_delete():
    stage = Stage()
    node = Node("node")
    stage.add_node(node)

    node["test"] = 5
    TEST_LOGGER.debug(f"Attributes: {node.attribs}")
    assert isinstance(node.attribs["test"], Attribute)

    node.delete_attr("test")
    TEST_LOGGER.debug(f"Attributes: {node.attribs}")
    assert "test" not in node.attribs


def test_attr_rename():
    stage = Stage()
    node = Node("node")
    stage.add_node(node)

    node.add_attr("test", value=5)
    old_raw = node.attr("test").get(raw=True)
    old_resolved = node.attr("test").get(resolved=True)
    old_cached = node.attr("test").get()

    TEST_LOGGER.debug(f"Before rename: {node.attribs}")
    node.rename_attr("test", "new_test")
    TEST_LOGGER.debug(f"After rename: {node.attribs}")
    assert "test" not in node.attribs
    assert "new_test" in node.attribs
    assert node["new_test"].value == old_raw
    assert node["new_test"].resolved_value == old_resolved
    assert node["new_test"].cached_value == old_cached


def test_attr_serialize():
    stage = Stage()
    parent_node = Node("node")
    stage.add_node(parent_node)

    node = Node("node1", parent=parent_node)
    node.add_attr("test", value=2)

    TEST_LOGGER.debug(node["test"])
    attr = node["test"]
    serial_data = attr.serialize()
    TEST_LOGGER.debug(f"Serialized: {serial_data}")

    assert serial_data["uuid"] == attr.uuid
    assert serial_data["name"] == attr.name
    if file_fn.is_jsonable(attr.value):
        assert serial_data["value"] == attr.value
    else:
        assert serial_data["value"] is None


def test_attr_deserialize():
    stage = Stage()
    node = Node("node")
    stage.add_node(node)
    node.add_attr("test", value=2)

    serial_data = node["test"].serialize()
    TEST_LOGGER.debug(f"Serialized: {serial_data}")

    node2 = Node("node2")
    stage.add_node(node)
    node2["test"] = None
    node2["test"].deserialize(serial_data, restore_id=True)
    new_attr = node2["test"]
    TEST_LOGGER.debug(f"Deserialized: {new_attr}")

    assert new_attr.uuid == node["test"].uuid
    assert new_attr.name == node["test"].name
    assert new_attr.value == node["test"].value


def test_attr_same_scope():
    stage = Stage()
    node = Node("node")
    stage.add_node(node)
    node.add_attr("test", value=2)

    child1 = Node("child", parent=node)
    child2 = Node("child", parent=node)

    child1.add_attr("count", value=5)
    child2.add_attr("len", value=10)

    TEST_LOGGER.debug(f"{child1['count']} | Scope: {child1['count'].node.scope}")
    TEST_LOGGER.debug(f"{child2['len']} | Scope: {child2['len'].node.scope}")
    TEST_LOGGER.debug(f"{node['test']} | Scope: {node['test'].node.scope}")

    assert child1["count"].same_scope_with(child2["len"])
    assert not child1["count"].same_scope_with(node["test"])


def test_attr_resolve_number():
    stage = Stage()
    node = Node("node")
    stage.add_node(node)
    node.add_attr("test", value=2, resolve=True)

    TEST_LOGGER.debug(node["test"])
    assert node["test"].resolved_value == 2


def test_attr_resolve_invalid_path():
    stage = Stage()
    node = Node("node")
    stage.add_node(node)
    node.add_attr("test")
    node["test"].set("/non_existing_node.test")

    assert node["test"].value == node["test"].resolved_value


def test_attr_resolve_non_existing_attr():
    stage = Stage()
    node = Node("node")
    stage.add_node(node)
    node.add_attr("test", value=5)

    child = Node(name="child", parent=node)
    child["test_rel"] = ""
    child["test_rel"].set("{..}{bad_attr}")

    assert child["test_rel"].resolved_value != node["test"].value
    assert child["test_rel"].resolved_value == child["test_rel"].value


def test_attr_resolve_recursive_path():
    stage = Stage()

    node1 = Node("node1")
    stage.add_node(node1)
    node1.add_attr("test1", value=5)

    node2 = Node("node2")
    stage.add_node(node2)
    node2.add_attr("test2", value="/node1.test1", resolve=True)

    node3 = Node("node3")
    stage.add_node(node3)
    node3.add_attr("test3", value="/node2.test2", resolve=True)

    TEST_LOGGER.debug(stage.describe())

    assert node3["test3"].resolved_value == node2["test2"].resolved_value
    assert node3["test3"].resolved_value == node1["test1"].value
    assert node2["test2"].resolved_value == node1["test1"].value


def test_attr_resolve_from_absolute_path():
    stage = Stage()
    node = Node()
    stage.add_node(node)

    child1 = Node("child1", parent=node)
    child2 = Node("child2", parent=node)

    leaf1 = Node("leaf1", parent=child1)
    leaf2 = Node("leaf2", parent=child2)

    leaf1.add_attr("test1", value="test_value")
    leaf2.add_attr("test2", value="/node/child1/leaf1.test1", resolve=True)

    assert leaf2.attr("test2").resolved_value == leaf1.attr("test1").resolved_value


def test_attr_connect():
    stage = Stage()
    node = Node()
    stage.add_node(node)

    child1 = Node("child1", parent=node)
    child2 = Node("child2", parent=node)

    child1.add_attr("test1", value=5)
    child2.add_attr("test2")

    child1["test1"].connect(child2["test2"])

    expected_value = f"{child1.path.as_posix()}.{child1['test1'].name}"
    assert child2["test2"].value == expected_value
    assert child2["test2"].resolved_value == 5
    assert child2["test2"].cached_value is None
