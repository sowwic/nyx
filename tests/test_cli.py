import logging

import pytest
from nyx_bridge.client import NyxClient

from nyx import cli
from nyx.api.v1 import CoreNodes, Stage, commands
from nyx.core import session as session_module


@pytest.fixture
def bridge_in_tmp(qapp, tmp_path, monkeypatch):
    """Keep the CLI's bridge server on a free port and its address file in tmp_path."""
    address_file = tmp_path / "bridge.json"
    monkeypatch.setattr(session_module, "BRIDGE_ADDRESS_FILE_PATH", address_file)
    monkeypatch.setattr(qapp.session, "_bridge_server", None)
    monkeypatch.setattr(qapp.session.config.values.bridge, "port", 0)
    monkeypatch.setattr(qapp.session.config.values.bridge, "enabled", True)
    yield address_file
    qapp.session.shutdown()


def create(stage, type_id, parent=None, name=None):
    command = commands.CreateNodeCommand(
        stage=stage, type_id=type_id, parent_node=parent, name=name
    )
    stage.push_command(command)
    return command.result_node


def save_stage(tmp_path, *node_types, name="stage.nyx"):
    """Save flow_start -> node_types chained by flow, return the file and the stage."""
    stage = Stage()
    previous = create(stage, CoreNodes.FLOW_START)
    nodes = []
    for type_id in node_types:
        node = create(stage, type_id)
        previous["flow"] >> node["flow"]
        previous = node
        nodes.append(node)
    path = tmp_path / name
    stage.export_json(path)
    return path, stage, nodes


def test_parser_reads_the_run_command():
    args = cli.build_parser().parse_args(["stage", "run", "a.nyx", "--no-bridge"])

    assert (args.command, args.stage_command) == ("stage", "run")
    assert str(args.path) == "a.nyx"
    assert args.bridge is False and args.port is None


def test_alias_parser_has_the_same_arguments():
    args = cli.build_run_stage_parser().parse_args(["a.nyx", "--port", "5000"])

    assert str(args.path) == "a.nyx"
    assert args.bridge is True and args.port == 5000


def test_parser_without_command_means_the_editor():
    assert cli.build_parser().parse_args([]).command is None


@pytest.mark.parametrize("argv", [["stage"], ["stage", "run"], ["stage", "nope"]])
def test_parser_rejects_incomplete_commands(argv):
    with pytest.raises(SystemExit) as info:
        cli.build_parser().parse_args(argv)

    assert info.value.code == cli.EXIT_USAGE


def test_run_stage_runs_the_stage_and_returns_zero(tmp_path, caplog, bridge_in_tmp):
    path, _, (log_node,) = save_stage(tmp_path, CoreNodes.LOG)
    log_node["message"].push_value("hello from the cli")
    log_node.stage.export_json(path)

    with caplog.at_level(logging.INFO):
        code = cli.run_stage(path, bridge=False)

    assert code == cli.EXIT_OK
    assert "hello from the cli" in caplog.text


def test_run_stage_returns_one_and_names_the_failed_node(
    tmp_path, caplog, bridge_in_tmp
):
    path, _, (client_node,) = save_stage(tmp_path, CoreNodes.REMOTE_CLIENT)

    code = cli.run_stage(path, bridge=False)

    assert code == cli.EXIT_STAGE_FAILED
    assert f"Stage failed at {client_node.path.as_posix()}" in caplog.text
    assert "not running" in caplog.text


def test_run_stage_returns_two_for_missing_and_invalid_files(
    tmp_path, caplog, bridge_in_tmp
):
    broken = tmp_path / "broken.nyx"
    broken.write_text("not json")

    assert cli.run_stage(tmp_path / "missing.nyx", bridge=False) == cli.EXIT_USAGE
    assert cli.run_stage(broken, bridge=False) == cli.EXIT_USAGE
    assert "not found" in caplog.text


def test_run_stage_without_bridge_starts_no_server(tmp_path, qapp, bridge_in_tmp):
    path, _, _ = save_stage(tmp_path, CoreNodes.LOG)

    cli.run_stage(path, bridge=False)

    assert qapp.session.bridge_server is None
    assert not bridge_in_tmp.exists()


def test_run_stage_starts_the_bridge_and_stops_it_afterwards(
    tmp_path, qapp, bridge_in_tmp
):
    path, _, _ = save_stage(tmp_path, CoreNodes.LOG)

    assert cli.run_stage(path) == cli.EXIT_OK

    server = qapp.session.bridge_server
    assert server is not None and not server.is_running
    assert not bridge_in_tmp.exists()


def test_port_option_overrides_the_configured_port(tmp_path, qapp, bridge_in_tmp):
    import socket

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        free_port = probe.getsockname()[1]
    path, _, _ = save_stage(tmp_path, CoreNodes.LOG)

    cli.run_stage(path, port=free_port)

    assert qapp.session.bridge_server.port == free_port


def test_remote_nodes_run_against_a_client_found_through_the_address_file(
    tmp_path, qapp, bridge_in_tmp, monkeypatch
):
    from nyx_bridge import protocol

    path, stage, (client_node,) = save_stage(tmp_path, CoreNodes.REMOTE_CLIENT)
    client_node["timeout"].push_value(10)
    action = create(stage, CoreNodes.REMOTE_ACTION, parent=client_node.path)
    inner_start = create(stage, CoreNodes.FLOW_START, parent=client_node.path)
    inner_start["flow"] >> action["flow"]
    script = tmp_path / "script.py"
    script.write_text("result = 6 * 7")
    action["script"].push_value(str(script))
    stage.export_json(path)

    monkeypatch.setattr(protocol, "default_address_file_path", lambda: bridge_in_tmp)
    monkeypatch.delenv(protocol.ADDRESS_ENV_VAR, raising=False)
    monkeypatch.delenv(protocol.ADDRESS_FILE_ENV_VAR, raising=False)

    client = NyxClient(name="cli-test", reconnect=False)
    thread = client.start_in_thread(connect_timeout=15)
    try:
        code = cli.run_stage(path)
    finally:
        client.stop()
        thread.join(timeout=5)

    assert code == cli.EXIT_OK
