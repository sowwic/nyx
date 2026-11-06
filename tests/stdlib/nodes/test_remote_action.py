import sys
import time

import pytest
from nyx_bridge.client import NyxClient
from nyx_bridge.server import RemoteExecutionError

from nyx.core import session as session_module
from nyx.api.v1 import CoreDatatypes, CoreNodeComponents, CoreNodes, Stage, commands
from nyx.stdlib.nodes.remote_action import RemoteActionNode

STAGES = []
"""Stages of the running test: a node doesn't keep its stage alive, so a test holding
only the node would lose the stage to the garbage collector."""


SCRIPT_DIR = []
"""Folder the scripts of the running test are written to."""


@pytest.fixture(autouse=True)
def keep_stages_alive(tmp_path):
    SCRIPT_DIR[:] = [tmp_path]
    yield
    STAGES.clear()
    SCRIPT_DIR.clear()


def write_script(source):
    """Write a script file and return its path."""
    path = SCRIPT_DIR[0] / f"script_{len(list(SCRIPT_DIR[0].glob('*.py')))}.py"
    path.write_text(source)
    return str(path)


@pytest.fixture
def server(qapp, tmp_path, monkeypatch):
    """Server of the application session, as the Remote Client node finds it."""
    session = qapp.session
    monkeypatch.setattr(session_module, "BRIDGE_ADDRESS_FILE_PATH", tmp_path / "b.json")
    monkeypatch.setattr(session, "_bridge_server", None)
    monkeypatch.setattr(session.config.values.bridge, "port", 0)
    running = session.start_bridge_server()
    yield running
    session.shutdown()


@pytest.fixture
def client(server):
    """Connected client serving from a thread."""
    host, port = server.host, server.port
    running = NyxClient(
        name="tester", address=(host, port), token=server.token, reconnect=False
    )
    running.start_in_thread()
    server.wait_for_client(name="tester", timeout=5)
    yield running
    running.stop()


def create(stage, type_id, parent=None, name=None):
    command = commands.CreateNodeCommand(
        stage=stage, type_id=type_id, parent_node=parent, name=name
    )
    stage.push_command(command)
    return command.result_node


def build_stage(*scripts, args=None, with_connection=True):
    """Build flow_start -> remote_client, and remote_action nodes inside of it.

    The remote_action nodes follow each other in the order of `scripts`, sources of
    script files. Without a connection they are on the stage root instead.
    """
    stage = Stage()
    STAGES.append(stage)
    start = create(stage, CoreNodes.FLOW_START)
    connection = None
    parent = None
    if with_connection:
        connection = create(stage, CoreNodes.REMOTE_CLIENT)
        start["flow"] >> connection["flow"]
        create(stage, CoreNodes.FLOW_START, parent=connection.path)
        parent = connection.path
        previous = connection.find_flow_start_node()
    else:
        previous = start

    scripts_nodes = []
    for script in scripts:
        node = create(stage, CoreNodes.REMOTE_ACTION, parent=parent)
        node["script"].push_value(write_script(script))
        previous["flow"] >> node["flow"]
        previous = node
        scripts_nodes.append(node)
    if args is not None:
        scripts_nodes[0]["args"].push_value(args)
    return stage, connection, scripts_nodes


def test_remote_action_node_creation():
    stage = Stage()
    STAGES.append(stage)
    node = create(stage, CoreNodes.REMOTE_ACTION)

    assert node["flow"].readable and node["flow"].writable
    assert node["script"].get_type_id() == CoreNodeComponents.REMOTE_SCRIPT
    assert node["script"].datatype_id == CoreDatatypes.STRING
    assert node["script"].writable and not node["script"].readable
    assert node["args"].datatype_id == CoreDatatypes.DICT
    assert node["args"].writable and not node["args"].readable
    assert node["timeout"].datatype_id == CoreDatatypes.FLOAT
    assert node["response"].datatype_id == CoreDatatypes.OBJECT
    assert node["response"].readable and not node["response"].writable
    assert not node["response"].is_editable
    assert all(node[name].is_editable for name in ("script", "args", "timeout"))
    assert node.get_description()


def test_remote_client_node_creation():
    stage = Stage()
    STAGES.append(stage)
    node = create(stage, CoreNodes.REMOTE_CLIENT)

    assert node["client_name"].datatype_id == CoreDatatypes.STRING
    assert node["timeout"].datatype_id == CoreDatatypes.FLOAT
    assert node["client"].readable and not node["client"].writable
    assert not node["client"].is_editable
    for name in ("client_name", "client_kind", "timeout"):
        assert node[name].is_editable and node[name].writable
    assert node.get_description()


def test_response_is_what_the_script_assigned_to_result(client):
    stage, connection, (node,) = build_stage(
        "result = {'module': 'arm_L', 'nodes': ['a', 'b'], 'count': n * 2}",
        args={"n": 21},
    )

    stage.crawler.start()

    assert node["response"].pull_value() == {
        "module": "arm_L",
        "nodes": ["a", "b"],
        "count": 42,
    }
    assert connection["client"].pull_value() == "tester"


def test_nodes_inside_a_connection_share_the_client_namespace(client):
    stage, _, (first, second) = build_stage("counter = 41", "result = counter + 1")

    stage.crawler.start()

    assert second["response"].pull_value() == 42


def test_connection_selects_the_client_by_name_and_kind(client):
    stage, connection, (node,) = build_stage("result = 1")
    connection["client_name"].push_value("tester")
    connection["client_kind"].push_value("python")

    stage.crawler.start()

    assert node["response"].pull_value() == 1


def test_connection_fails_when_no_client_connects(server):
    stage, connection, _ = build_stage("result = 1")
    connection["timeout"].push_value(0.2)

    start = time.monotonic()
    with pytest.raises(TimeoutError, match="within"):
        stage.crawler.start()

    assert time.monotonic() - start < 5


def test_connection_fails_when_the_server_is_not_running(server):
    server.stop()
    stage, _, _ = build_stage("result = 1")

    with pytest.raises(RuntimeError, match="not running"):
        stage.crawler.start()


def test_script_error_fails_the_node_with_the_remote_error(client):
    stage, _, (node,) = build_stage("raise ValueError('bad module')")

    with pytest.raises(RemoteExecutionError, match="ValueError: bad module") as info:
        stage.crawler.start()

    assert "Traceback" in info.value.remote_traceback
    assert stage.crawler.context.scope_depth == 0


def test_remote_action_outside_a_connection_fails(client):
    stage, _, (node,) = build_stage("result = 1", with_connection=False)

    with pytest.raises(LookupError, match="ClientSession"):
        stage.crawler.start()


def test_scope_ends_with_the_connection_node(client):
    stage, connection, (inside,) = build_stage("result = 1")
    after = create(stage, CoreNodes.REMOTE_ACTION, name="after")
    after["script"].push_value("result = 2")
    connection["flow"] >> after["flow"]

    with pytest.raises(LookupError):
        stage.crawler.start()

    assert inside["response"].pull_value() == 1


def test_script_output_is_logged_not_stored(client, caplog):
    stage, _, (node,) = build_stage("print('hello from the client')")

    with caplog.at_level("INFO"):
        stage.crawler.start()

    assert "hello from the client" in caplog.text
    assert node["response"].pull_value() is None


def test_subclasses_customise_the_script_args_and_response(client, monkeypatch):
    stage, _, (node,) = build_stage("")
    handled = []
    monkeypatch.setattr(
        RemoteActionNode, "build_script", lambda self, args: "result = side * 2"
    )
    monkeypatch.setattr(RemoteActionNode, "build_args", lambda self: {"side": "L"})
    monkeypatch.setattr(
        RemoteActionNode,
        "handle_response",
        lambda self, response: handled.append(response),
    )

    stage.crawler.start()

    assert handled == ["LL"]


def test_script_value_is_kept_as_text_and_never_evaluated_in_nyx():
    stage = Stage()
    STAGES.append(stage)
    node = create(stage, CoreNodes.REMOTE_ACTION)

    node["script"].push_value("__import__('sys').modules['ran_in_nyx'] = 1")
    node["script"].push_value("1 + 1")

    assert node["script"].pull_value() == "1 + 1"
    assert "ran_in_nyx" not in sys.modules


def test_entry_point_is_called_in_the_client_with_the_args_as_keywords(
    client, monkeypatch
):
    (SCRIPT_DIR[0] / "rig_tools.py").write_text(
        "def create_rig_module(module_type, side='C'):\n"
        "    return {'module': f'{module_type}_{side}', 'nodes': [1, 2]}\n"
    )
    monkeypatch.syspath_prepend(str(SCRIPT_DIR[0]))
    stage, _, (node,) = build_stage("", args={"module_type": "arm", "side": "L"})
    node["script"].push_value("rig_tools:create_rig_module")

    stage.crawler.start()

    assert node["response"].pull_value() == {"module": "arm_L", "nodes": [1, 2]}


def test_entry_point_that_does_not_exist_in_the_client_fails_there(client):
    stage, _, (node,) = build_stage("")
    node["script"].push_value("no_such_module_anywhere:main")

    with pytest.raises(RemoteExecutionError, match="ModuleNotFoundError"):
        stage.crawler.start()


@pytest.mark.parametrize("value", ["", "not a path or entry point", "missing/file.py"])
def test_script_that_is_neither_a_file_nor_an_entry_point_fails_before_sending(
    client, value
):
    stage, _, (node,) = build_stage("")
    node["script"].push_value(value)

    with pytest.raises(ValueError, match="script"):
        stage.crawler.start()


def test_script_survives_saving_and_loading_as_text(tmp_path):
    node = create(Stage(), CoreNodes.REMOTE_ACTION, name="saved")
    STAGES.append(node.stage)
    node["script"].push_value("tools:main")
    file_path = tmp_path / "script.nyx"
    node.export_to_json(file_path)

    restored = create(Stage(), CoreNodes.REMOTE_ACTION, name="restored")
    STAGES.append(restored.stage)
    restored["script"].push_value("other:main")
    restored.load_from_json(file_path)

    assert restored["script"].pull_value() == "tools:main"
