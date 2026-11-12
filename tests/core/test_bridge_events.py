from nyx_bridge.client import NyxClient


def connect(server, name):
    client = NyxClient(name=name, address=("127.0.0.1", server.port), token=server.token)
    client.connect()
    return client


def test_signals_follow_the_server_and_its_clients(bridge_session, qtbot):
    events = bridge_session.bridge_events

    with qtbot.waitSignal(events.started, timeout=5000):
        server = bridge_session.start_bridge_server()
    with qtbot.waitSignal(events.clients_changed, timeout=5000):
        client = connect(server, "one")
    with qtbot.waitSignal(events.clients_changed, timeout=5000):
        server.wait_for_client(name="one", timeout=5).close()
    with qtbot.waitSignal(events.stopped, timeout=5000):
        bridge_session.stop_bridge_server()
    client.stop()


def test_stopped_server_starts_again_with_the_same_token(bridge_session):
    server = bridge_session.start_bridge_server()
    token = server.token

    bridge_session.stop_bridge_server()
    assert not server.is_running
    again = bridge_session.start_bridge_server()

    assert again is server
    assert again.is_running
    assert again.token == token
