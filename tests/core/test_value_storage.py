import typing

import pytest

from nyx.core.value_storage import ValueStorage
from nyx.core.node_component import NodeComponent
from nyx.static.enums import NodeComponentValueMask


class UpperStorage(ValueStorage):
    def compute_value(self) -> typing.Any:
        return str(self.raw_value).upper()


class UpperComponent(NodeComponent):
    VALUE_STORAGE_CLS = UpperStorage

    @classmethod
    def get_type_id(cls) -> str:
        return "test:upper"


def test_component_uses_default_storage():
    assert NodeComponent.VALUE_STORAGE_CLS is ValueStorage


def test_push_evaluates_strings():
    component = UpperComponent()
    component.push_value("abc")
    assert component.raw_value == "abc"
    assert component.cached_value == "ABC"
    assert component.display_value == "ABC"


def test_push_without_evaluation_keeps_raw_as_cache():
    component = UpperComponent()
    component.push_value("abc", evaluate=False)
    assert component.cached_value == "abc"


def test_clear_cache_resets_display_to_raw():
    component = UpperComponent()
    component.push_value("abc")
    component.clear_cached_value()
    assert component.cached_value is None
    assert component.display_value == "abc"


@pytest.mark.parametrize(
    "mask, expected",
    [
        (NodeComponentValueMask.RAW, "abc"),
        (NodeComponentValueMask.CACHE, "ABC"),
        (NodeComponentValueMask.DISPLAY, "ABC"),
    ],
)
def test_pull_by_mask(mask, expected):
    component = UpperComponent()
    component.push_value("abc")
    assert component.value_storage.pull(mask) == expected
