import pytest

from nyx.api.v1 import Stage, CoreNodes, CoreDatatypes
from stage_helpers import create_node


@pytest.mark.parametrize(
    ("datatype_id", "expected"),
    [
        (CoreDatatypes.STRING, ""),
        (CoreDatatypes.INT, 0),
        (CoreDatatypes.BOOL, False),
    ],
)
def test_default_follows_the_datatype(datatype_id, expected):
    component = create_node(Stage(), CoreNodes.BRANCH)["condition"]
    component.set_datatype(datatype_id)
    assert component.default_value == expected
    assert type(component.default_value) is type(expected)


def test_new_component_default_is_the_initial_value():
    component = create_node(Stage(), CoreNodes.BRANCH)["condition"]
    assert component.default_value == component.get_initial_value()


def test_custom_default_is_cast_to_the_new_datatype():
    component = create_node(Stage(), CoreNodes.BRANCH)["condition"]
    component.set_datatype(CoreDatatypes.INT)
    component.default_value = 5

    component.set_datatype(CoreDatatypes.STRING)

    assert component.default_value == "5"


def test_custom_default_that_cant_be_cast_is_replaced():
    component = create_node(Stage(), CoreNodes.BRANCH)["condition"]
    component.set_datatype(CoreDatatypes.STRING)
    component.default_value = "abc"

    component.set_datatype(CoreDatatypes.INT)

    assert component.default_value == 0
