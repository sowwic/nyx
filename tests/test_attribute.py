from nyx import get_main_logger
from nyx.core import Stage
from nyx.core import Node
from nyx.core.attribute import Attribute
from nyx.utils import file_fn


LOGGER = get_main_logger()


def test_attr_getset():
    stage = Stage()
    parent_node = Node("node")
    stage.add_node(parent_node)

    node = Node("node1", parent=parent_node)
    stage.add_node(node)
    node["test"] = 2
    assert isinstance(node.attribs["test"], Attribute)
    assert node["test"].value == 2
    assert node["test"].readable
    assert node["test"].writable


def test_attr_delete():
    stage = Stage()
    node = Node("node")
    stage.add_node(node)

    node["test"] = 5
    LOGGER.debug(f"Attributes: {node.attribs}")
    assert isinstance(node.attribs["test"], Attribute)

    node.delete_attr("test")
    LOGGER.debug(f"Attributes: {node.attribs}")
    assert "test" not in node.attribs


def test_attr_rename():
    stage = Stage()
    node = Node("node")
    stage.add_node(node)

    node["test"] = 5
    LOGGER.debug(f"Attributes: {node.attribs}")
    node.rename_attr("test", "new_test")
    assert "test" not in node.attribs
    assert "new_test" in node.attribs
    assert node["new_test"].value == 5


def test_attr_serialize():
    stage = Stage()
    parent_node = Node("node")
    stage.add_node(parent_node)

    node = Node("node1", parent=parent_node)
    node["test"] = 2

    LOGGER.debug(node["test"])
    attr = node["test"]
    serial_data = attr.serialize()
    LOGGER.debug(f"Serialized: {serial_data}")

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
    node["test"] = 2

    serial_data = node["test"].serialize()
    LOGGER.debug(f"Serialized: {serial_data}")

    node2 = Node("node2")
    stage.add_node(node)
    hashmap = {}
    node2["test"] = None
    node2["test"].deserialize(serial_data, hashmap=hashmap, restore_id=True)
    new_attr = node2["test"]
    LOGGER.debug(f"Deserialized: {new_attr}")
    LOGGER.debug(f"Hashmap: {hashmap}")

    assert new_attr.uuid == node["test"].uuid
    assert new_attr.name == node["test"].name
    assert new_attr.value == node["test"].value
    assert new_attr.readable == node["test"].readable
    assert new_attr.writable == node["test"].writable
