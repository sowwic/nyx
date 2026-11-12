import sys
import time

import pytest
from nyx_bridge.client import NyxClient
from nyx_bridge.server import RemoteExecutionError

from nyx.api.v1 import CoreDatatypes, CoreNodeComponents, CoreNodes, Stage
from nyx.stdlib.nodes.remote_action import RemoteActionNode
from stage_helpers import STAGES, create_node

"""Stages of the running test: a node doesn't keep its stage alive, so a test holding
only the node would lose the stage to the garbage collector."""


SCRIPT_DIR = []
"""Folder the scripts of the running test are written to."""


@pytest.fixture(autouse=True)
def script_dir(tmp_path):
    SCRIPT_DIR[:] = [tmp_path]
    yield
    SCRIPT_DIR.clear()


def write_script(source):
    """Write a script file and return its path."""
    path = SCRIPT_DIR[0] / f"script_{len(list(SCRIPT_DIR[0].glob('*.py')))}.py"
    path.write_text(source)
    return str(path)


@pytest.fixture
def bridge_client(bridge_server):
    """Connected client serving from a thread."""
    host, port = bridge_server.host, bridge_server.port
    running = NyxClient(
        name="tester", address=(host, port), token=bridge_server.token, reconnect=False
    )
    running.start_in_thread()
    bridge_server.wait_for_client(name="tester", timeout=5)
    yield running
    running.stop()


def build_stage(*scripts, args=None, with_connection=True):
    """Build flow_start -> remote_client, and remote_action nodes inside of it.

    The remote_action nodes follow each other in the order of `scripts`, sources of
    script files. Without a connection they are on the stage root instead.
    """
    stage = Stage()
    STAGES.append(stage)
    start = create_node(stage, CoreNodes.FLOW_START)
    connection = None
    parent = None
    if with_connection:
        connection = create_node(stage, CoreNodes.REMOTE_CLIENT)
        start["flow"] >> connection["flow"]
        create_node(stage, CoreNodes.FLOW_START, parent=connection.path)
        parent = connection.path
        previous = connection.find_flow_start_node()
    else:
        previous = start

    scripts_nodes = []
    for script in scripts:
        node = create_node(stage, CoreNodes.REMOTE_ACTION, parent=parent)
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
    node = create_node(stage, CoreNodes.REMOTE_ACTION)

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
    node = create_node(stage, CoreNodes.REMOTE_CLIENT)

    assert node["client_name"].datatype_id == CoreDatatypes.STRING
    assert node["timeout"].datatype_id == CoreDatatypes.FLOAT
    assert node["client"].readable and not node["client"].writable
    assert not node["client"].is_editable
    for name in ("client_name", "client_kind", "timeout"):
        assert node[name].is_editable and node[name].writable
    assert node.get_description()


def test_response_is_what_the_script_assigned_to_result(bridge_client):
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


def test_nodes_inside_a_connection_share_the_client_namespace(bridge_client):
    stage, _, (first, second) = build_stage("counter = 41", "result = counter + 1")

    stage.crawler.start()

    assert second["response"].pull_value() == 42


def test_connection_selects_the_client_by_name_and_kind(bridge_client):
    stage, connection, (node,) = build_stage("result = 1")
    connection["client_name"].push_value("tester")
    connection["client_kind"].push_value("python")

    stage.crawler.start()

    assert node["response"].pull_value() == 1


def test_connection_fails_when_no_client_connects(bridge_server):
    stage, connection, _ = build_stage("result = 1")
    connection["timeout"].push_value(0.2)

    start = time.monotonic()
    with pytest.raises(TimeoutError, match="within"):
        stage.crawler.start()

    assert time.monotonic() - start < 5


def test_connection_fails_when_the_server_is_not_running(bridge_server):
    bridge_server.stop()
    stage, _, _ = build_stage("result = 1")

    with pytest.raises(RuntimeError, match="not running"):
        stage.crawler.start()


class OtherKindClient(NyxClient):
    CLIENT_KIND = "other"


@pytest.fixture
def two_clients(bridge_server, bridge_client):
    """The `tester` client (kind python) and a second one of another kind."""
    other = OtherKindClient(
        name="second",
        address=(bridge_server.host, bridge_server.port),
        token=bridge_server.token,
        reconnect=False,
    )
    other.start_in_thread()
    bridge_server.wait_for_client(name="second", timeout=5)
    yield bridge_client, other
    other.stop()


def test_connection_fails_when_several_clients_match_instead_of_picking_one(
    two_clients,
):
    stage, _, (node,) = build_stage("result = 1")

    with pytest.raises(LookupError, match="2 connected clients match") as info:
        stage.crawler.start()

    message = str(info.value)
    assert "tester (python)" in message and "second (other)" in message
    assert node["response"].pull_value() is None
    assert stage.crawler.context.scope_depth == 0


def test_connection_with_a_kind_picks_the_one_of_that_kind(two_clients):
    stage, connection, (node,) = build_stage("result = 'where'")
    connection["client_kind"].push_value("other")

    stage.crawler.start()

    assert connection["client"].pull_value() == "second"
    assert node["response"].pull_value() == "where"


@pytest.mark.parametrize("text", ["max", "1 + 1", "None"])
def test_client_name_and_kind_are_kept_as_typed(text):
    stage = Stage()
    STAGES.append(stage)
    node = create_node(stage, CoreNodes.REMOTE_CLIENT)

    node["client_name"].push_value(text)
    node["client_kind"].push_value(text)

    assert node["client_name"].pull_value() == text
    assert node["client_kind"].pull_value() == text


def test_connection_with_a_name_picks_the_one_with_that_name(two_clients):
    stage, connection, _ = build_stage("result = 1")
    connection["client_name"].push_value("tester")

    stage.crawler.start()

    assert connection["client"].pull_value() == "tester"


def test_script_error_fails_the_node_with_the_remote_error(bridge_client):
    stage, _, (node,) = build_stage("raise ValueError('bad module')")

    with pytest.raises(RemoteExecutionError, match="ValueError: bad module") as info:
        stage.crawler.start()

    assert "Traceback" in info.value.remote_traceback
    assert stage.crawler.context.scope_depth == 0


def test_remote_action_outside_a_connection_fails(bridge_client):
    stage, _, (node,) = build_stage("result = 1", with_connection=False)

    with pytest.raises(LookupError, match="ClientSession"):
        stage.crawler.start()


def test_scope_ends_with_the_connection_node(bridge_client):
    stage, connection, (inside,) = build_stage("result = 1")
    after = create_node(stage, CoreNodes.REMOTE_ACTION, name="after")
    after["script"].push_value("result = 2")
    connection["flow"] >> after["flow"]

    with pytest.raises(LookupError):
        stage.crawler.start()

    assert inside["response"].pull_value() == 1


def test_script_output_is_logged_not_stored(bridge_client, caplog):
    stage, _, (node,) = build_stage("print('hello from the client')")

    with caplog.at_level("INFO"):
        stage.crawler.start()

    assert "hello from the client" in caplog.text
    assert node["response"].pull_value() is None


def test_subclasses_customise_the_script_args_and_response(bridge_client, monkeypatch):
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
    node = create_node(stage, CoreNodes.REMOTE_ACTION)

    node["script"].push_value("__import__('sys').modules['ran_in_nyx'] = 1")
    node["script"].push_value("1 + 1")

    assert node["script"].pull_value() == "1 + 1"
    assert "ran_in_nyx" not in sys.modules


def test_entry_point_is_called_in_the_client_with_the_args_as_keywords(
    bridge_client, monkeypatch
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


def test_entry_point_that_does_not_exist_in_the_client_fails_there(bridge_client):
    stage, _, (node,) = build_stage("")
    node["script"].push_value("no_such_module_anywhere:main")

    with pytest.raises(RemoteExecutionError, match="ModuleNotFoundError"):
        stage.crawler.start()


def test_entry_point_can_go_through_the_attributes_of_a_module(bridge_client):
    stage, _, (node,) = build_stage("", args={"obj": {"a": 1}, "indent": None})
    node["script"].push_value("json:dumps")

    stage.crawler.start()

    assert node["response"].pull_value() == '{"a": 1}'

    node["script"].push_value("os.path:basename")
    node["args"].push_value({"p": "/some/where/file.txt"})
    stage.crawler.start()

    assert node["response"].pull_value() == "file.txt"


def write_attribute_namespace_module(monkeypatch):
    """A module with `ops.mesh.make`, an attribute chain like bpy.ops.mesh."""
    (SCRIPT_DIR[0] / "fake_ops.py").write_text(
        "import types\n"
        "def make(size=1, location=(0, 0, 0)):\n"
        "    return {'size': size, 'location': list(location)}\n"
        "ops = types.SimpleNamespace(mesh=types.SimpleNamespace(make=make))\n"
    )
    monkeypatch.syspath_prepend(str(SCRIPT_DIR[0]))


def test_entry_point_can_name_an_attribute_that_is_not_a_module(
    bridge_client, monkeypatch
):
    write_attribute_namespace_module(monkeypatch)
    stage, _, (node,) = build_stage("", args={"size": 2, "location": [0, 0, 1]})
    node["script"].push_value("fake_ops.ops.mesh:make")

    stage.crawler.start()

    assert node["response"].pull_value() == {"size": 2, "location": [0, 0, 1]}


def test_entry_point_with_a_missing_attribute_fails_there(bridge_client, monkeypatch):
    write_attribute_namespace_module(monkeypatch)
    stage, _, (node,) = build_stage("")
    node["script"].push_value("fake_ops.ops.nothing:make")

    with pytest.raises(RemoteExecutionError, match="AttributeError"):
        stage.crawler.start()


def test_entry_point_whose_module_fails_to_import_something_reports_that(
    bridge_client, monkeypatch
):
    (SCRIPT_DIR[0] / "needs_missing.py").write_text(
        "import a_dependency_nobody_has\n\ndef main():\n    pass\n"
    )
    monkeypatch.syspath_prepend(str(SCRIPT_DIR[0]))
    stage, _, (node,) = build_stage("")
    node["script"].push_value("needs_missing:main")

    with pytest.raises(RemoteExecutionError, match="a_dependency_nobody_has"):
        stage.crawler.start()


@pytest.mark.parametrize("value", ["", "not a path or entry point", "missing/file.py"])
def test_script_that_is_neither_a_file_nor_an_entry_point_fails_before_sending(
    bridge_client, value
):
    stage, _, (node,) = build_stage("")
    node["script"].push_value(value)

    with pytest.raises(ValueError, match="script"):
        stage.crawler.start()


def test_script_survives_saving_and_loading_as_text(tmp_path):
    node = create_node(Stage(), CoreNodes.REMOTE_ACTION, name="saved")
    STAGES.append(node.stage)
    node["script"].push_value("tools:main")
    file_path = tmp_path / "script.nyx"
    node.export_to_json(file_path)

    restored = create_node(Stage(), CoreNodes.REMOTE_ACTION, name="restored")
    STAGES.append(restored.stage)
    restored["script"].push_value("other:main")
    restored.load_from_json(file_path)

    assert restored["script"].pull_value() == "tools:main"
