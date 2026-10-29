import logging
import typing

import pytest

from nyx.api.v1 import BridgeServer, NYX_REGISTRY, NyxPlugin, NyxPluginManager
from nyx.core.session import NyxSession


class DemoServer(BridgeServer):
    TYPE_ID = "demo"


class OtherDemoServer(BridgeServer):
    TYPE_ID = "demo"


class UntypedServer(BridgeServer):
    pass


def make_plugin(plugin_id: str, *server_classes: type[BridgeServer]) -> type[NyxPlugin]:
    class ServerPlugin(NyxPlugin):
        @classmethod
        def get_type_id(cls) -> str:
            return plugin_id

        @classmethod
        def initialize(cls) -> typing.Self:
            plugin = cls()
            plugin.contents.servers.extend(server_classes)
            return plugin

    return ServerPlugin


@pytest.fixture
def register_plugins():
    """Register test plugins, and take them out again afterwards."""
    added = []

    def _register(*plugin_classes):
        for plugin_cls in plugin_classes:
            NYX_REGISTRY.add_plugin(plugin_cls)
            added.append(plugin_cls.get_type_id())
            NYX_REGISTRY.plugins[plugin_cls.get_type_id()].initialize()
        NYX_REGISTRY.register_plugin_content()

    yield _register

    for plugin_id in added:
        NYX_REGISTRY.plugins.pop(plugin_id, None)
    NYX_REGISTRY.register_plugin_content()


def test_plugin_servers_are_registered_by_type_id(register_plugins):
    register_plugins(make_plugin("ServersA", DemoServer))

    assert NYX_REGISTRY.get_server_cls("demo") is DemoServer
    assert NYX_REGISTRY.servers["demo"] is DemoServer
    assert NYX_REGISTRY.get_server_cls("missing") is None


def test_servers_of_a_removed_plugin_are_gone_after_rebuilding(register_plugins):
    register_plugins(make_plugin("ServersB", DemoServer))
    NYX_REGISTRY.plugins.pop("ServersB")

    NYX_REGISTRY.register_plugin_content()

    assert NYX_REGISTRY.get_server_cls("demo") is None


def test_duplicate_and_untyped_servers_are_skipped(register_plugins, caplog):
    with caplog.at_level(logging.ERROR, logger="NyxRegistry"):
        register_plugins(
            make_plugin("ServersC", DemoServer, UntypedServer),
            make_plugin("ServersD", OtherDemoServer),
        )

    assert NYX_REGISTRY.get_server_cls("demo") is DemoServer
    assert list(NYX_REGISTRY.servers) == ["demo"]
    assert "already registered" in caplog.text
    assert "empty TYPE_ID" in caplog.text


def test_session_creates_servers_of_registered_types(register_plugins):
    register_plugins(make_plugin("ServersE", DemoServer))
    session = NyxSession()

    server = session.bridge_servers.create_server("demo", port=0)

    assert isinstance(server, DemoServer)
    assert session.bridge_servers.get_server("demo") is server


def test_session_shutdown_stops_the_servers():
    session = NyxSession()
    server = session.bridge_servers.add_server(BridgeServer(name="s", port=0))
    server.start()

    session.shutdown()

    assert not server.is_running


def test_servers_are_stopped_when_the_application_quits(qapp, monkeypatch):
    server = qapp.session.bridge_servers.add_server(BridgeServer(name="quit", port=0))
    server.start()
    try:
        qapp.aboutToQuit.emit()

        assert not server.is_running
    finally:
        qapp.session.bridge_servers.remove_server("quit")


def test_plugin_manager_is_unaffected_by_plugins_without_servers():
    NyxPluginManager().initialize_plugins()

    assert NYX_REGISTRY.servers == {}
