import logging
import types

from nyx.api.v1 import CoreSpawners
from nyx.core.plugin_subsystem.plugin import NyxPluginContents
from nyx.core.plugin_subsystem.registry import NyxRegistry


class FakeSpawner:
    ID = "test.fake_spawner"

    @classmethod
    def get_type_id(cls) -> str:
        return cls.ID


class OtherFakeSpawner(FakeSpawner):
    pass


class ThirdFakeSpawner(FakeSpawner):
    ID = "test.third_spawner"


def plugin_entry(*spawner_classes):
    contents = types.SimpleNamespace(spawners=list(spawner_classes))
    return types.SimpleNamespace(
        plugin_instance=types.SimpleNamespace(contents=contents),
        plugin_cls=types.SimpleNamespace(get_type_id=lambda: "test:plugin"),
    )


def test_core_spawner_ids_are_unique_and_dotted():
    ids = [spawner_id.value for spawner_id in CoreSpawners]

    assert len(set(ids)) == len(ids)
    assert all(spawner_id.startswith("core.") for spawner_id in ids)


def test_plugin_contents_start_without_spawners():
    contents = NyxPluginContents()

    assert contents.spawners == []
    assert NyxPluginContents().spawners is not contents.spawners


def test_spawners_are_found_by_id_and_keep_the_order_they_were_registered_in():
    registry = NyxRegistry()

    registry.register_spawners(plugin_entry(ThirdFakeSpawner, FakeSpawner))

    assert list(registry.spawners) == [ThirdFakeSpawner.ID, FakeSpawner.ID]
    assert registry.get_spawner_cls(FakeSpawner.ID) is FakeSpawner
    assert registry.get_spawner_cls("test.nope") is None


def test_the_first_spawner_with_an_id_wins_and_the_second_is_reported(caplog):
    registry = NyxRegistry()

    with caplog.at_level(logging.ERROR):
        registry.register_spawners(plugin_entry(FakeSpawner, OtherFakeSpawner))

    assert registry.get_spawner_cls(FakeSpawner.ID) is FakeSpawner
    assert "OtherFakeSpawner" in caplog.text
    assert FakeSpawner.ID in caplog.text


def test_clear_drops_the_spawners():
    registry = NyxRegistry()
    registry.register_spawners(plugin_entry(FakeSpawner))

    registry.clear()

    assert registry.spawners == {}


def test_register_plugin_content_rebuilds_the_spawners_of_the_enabled_plugins():
    registry = NyxRegistry()
    registry.spawners["test.stale"] = FakeSpawner

    registry.register_plugin_content()

    assert registry.spawners == {}
