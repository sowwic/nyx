import logging
import types

from nyx.api.v1 import CoreCreators
from nyx.core.plugin_subsystem.plugin import NyxPluginContents
from nyx.core.plugin_subsystem.registry import NyxRegistry


class FakeCreator:
    ID = "test.fake_creator"

    @classmethod
    def get_type_id(cls) -> str:
        return cls.ID


class OtherFakeCreator(FakeCreator):
    pass


class ThirdFakeCreator(FakeCreator):
    ID = "test.third_creator"


def plugin_entry(*creator_classes):
    contents = types.SimpleNamespace(creators=list(creator_classes))
    return types.SimpleNamespace(
        plugin_instance=types.SimpleNamespace(contents=contents),
        plugin_cls=types.SimpleNamespace(get_type_id=lambda: "test:plugin"),
    )


def test_core_creator_ids_are_unique_and_dotted():
    ids = [creator_id.value for creator_id in CoreCreators]

    assert len(set(ids)) == len(ids)
    assert all(creator_id.startswith("core.") for creator_id in ids)


def test_plugin_contents_start_without_creators():
    contents = NyxPluginContents()

    assert contents.creators == []
    assert NyxPluginContents().creators is not contents.creators


def test_creators_are_found_by_id_and_keep_the_order_they_were_registered_in():
    registry = NyxRegistry()

    registry.register_creators(plugin_entry(ThirdFakeCreator, FakeCreator))

    assert list(registry.creators) == [ThirdFakeCreator.ID, FakeCreator.ID]
    assert registry.get_creator_cls(FakeCreator.ID) is FakeCreator
    assert registry.get_creator_cls("test.nope") is None


def test_the_first_creator_with_an_id_wins_and_the_second_is_reported(caplog):
    registry = NyxRegistry()

    with caplog.at_level(logging.ERROR):
        registry.register_creators(plugin_entry(FakeCreator, OtherFakeCreator))

    assert registry.get_creator_cls(FakeCreator.ID) is FakeCreator
    assert "OtherFakeCreator" in caplog.text
    assert FakeCreator.ID in caplog.text


def test_clear_drops_the_creators():
    registry = NyxRegistry()
    registry.register_creators(plugin_entry(FakeCreator))

    registry.clear()

    assert registry.creators == {}


def test_register_plugin_content_rebuilds_the_creators_of_the_enabled_plugins():
    registry = NyxRegistry()
    registry.creators["test.stale"] = FakeCreator

    registry.register_plugin_content()

    assert registry.creators == {}
