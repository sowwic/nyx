import os
import shlex
import sys
import time

import pytest
from nyx_bridge.client import NyxClient
from nyx_bridge.server import RemoteExecutionError

from nyx.api.v1 import CoreNodes, Stage
from stage_helpers import STAGES, create_node


SCRIPT_DIR = []
CLIENT_CODE = (
    "import os; from nyx_bridge.client import NyxClient; "
    "NyxClient(name=os.environ['NYX_BRIDGE_CLIENT_NAME'], reconnect=False)"
    ".serve_forever()"
)
CLIENT_COMMAND = f"{shlex.quote(sys.executable)} -c {shlex.quote(CLIENT_CODE)}"
SLEEP_COMMAND = f"{shlex.quote(sys.executable)} -c 'import time; time.sleep(60)'"


@pytest.fixture(autouse=True)
def script_dir(tmp_path):
    SCRIPT_DIR[:] = [tmp_path]
    yield
    SCRIPT_DIR.clear()


def build_stage(command, *scripts, remote_client=True):
    """Build flow_start -> launch_process [-> remote_client] -> remote_action nodes.

    Returns the stage, the launch node, the remote client (None without) and the
    actions. The actions run `scripts` (source text), each in a file.
    """
    stage = Stage()
    STAGES.append(stage)
    start = create_node(stage, CoreNodes.FLOW_START)
    launch = create_node(stage, CoreNodes.LAUNCH_PROCESS)
    start["flow"] >> launch["flow"]
    launch["command"].push_value(command)
    inner_start = create_node(stage, CoreNodes.FLOW_START, parent=launch.path)

    parent, previous, remote = launch.path, inner_start, None
    if remote_client:
        remote = create_node(stage, CoreNodes.REMOTE_CLIENT, parent=launch.path)
        inner_start["flow"] >> remote["flow"]
        parent = remote.path
        previous = create_node(stage, CoreNodes.FLOW_START, parent=remote.path)

    actions = []
    for index, source in enumerate(scripts):
        action = create_node(stage, CoreNodes.REMOTE_ACTION, parent=parent)
        path = SCRIPT_DIR[0] / f"script_{index}.py"
        path.write_text(source)
        action["script"].push_value(str(path))
        previous["flow"] >> action["flow"]
        previous = action
        actions.append(action)
    return stage, launch, remote, actions


def is_alive(pid):
    if sys.platform == "win32":
        # os.kill(pid, 0) would terminate the process on Windows.
        import ctypes

        kernel32 = ctypes.windll.kernel32
        kernel32.OpenProcess.restype = ctypes.c_void_p
        handle = kernel32.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            kernel32.GetExitCodeProcess(ctypes.c_void_p(handle), ctypes.byref(code))
            return code.value == 259  # STILL_ACTIVE
        finally:
            kernel32.CloseHandle(ctypes.c_void_p(handle))
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def wait_until_gone(pid, timeout=10):
    deadline = time.monotonic() + timeout
    while is_alive(pid) and time.monotonic() < deadline:
        time.sleep(0.05)
    return not is_alive(pid)


def test_launched_client_connects_and_the_nodes_inside_run_in_it(bridge_server):
    stage, launch, _, (action,) = build_stage(
        CLIENT_COMMAND, "import os\nresult = os.environ['NYX_BRIDGE_CLIENT_NAME']"
    )

    stage.crawler.start()

    # Not compared by pid: a venv python on Windows starts the real one as a child.
    assert launch["process_id"].pull_value()
    assert action["response"].pull_value() == launch["client"].pull_value()
    assert launch["client"].pull_value().startswith("launched-")


def test_the_process_is_stopped_when_the_stage_is_done(bridge_server):
    stage, launch, _, _ = build_stage(CLIENT_COMMAND, "result = 1")

    stage.crawler.start()

    assert wait_until_gone(launch["process_id"].pull_value())
    assert not bridge_server.clients


def test_the_process_is_stopped_when_a_node_inside_fails(bridge_server):
    stage, launch, _, _ = build_stage(CLIENT_COMMAND, "raise ValueError('inside')")

    with pytest.raises(RemoteExecutionError, match="inside"):
        stage.crawler.start()

    assert wait_until_gone(launch["process_id"].pull_value())


def test_the_bridge_settings_are_in_the_environment_of_the_process(bridge_server):
    source = (
        "import os\n"
        "result = {k: os.environ.get(k) for k in ('NYX_BRIDGE_ADDRESS', "
        "'NYX_BRIDGE_TOKEN', 'NYX_BRIDGE_CLIENT_NAME')}"
    )
    stage, launch, _, (action,) = build_stage(CLIENT_COMMAND, source)

    stage.crawler.start()

    assert action["response"].pull_value() == {
        "NYX_BRIDGE_ADDRESS": f"{bridge_server.host}:{bridge_server.port}",
        "NYX_BRIDGE_TOKEN": bridge_server.token,
        "NYX_BRIDGE_CLIENT_NAME": launch["client"].pull_value(),
    }


def test_variables_of_env_are_expanded_in_the_command_and_given_to_the_process(
    bridge_server, tmp_path
):
    command = f'"$PYEXE" -c {shlex.quote(CLIENT_CODE)}'
    source = (
        "import os\nresult = [os.environ['PYEXE'], os.environ['EXTRA'], os.getcwd()]"
    )
    stage, launch, _, (action,) = build_stage(command, source)
    launch["env"].push_value({"PYEXE": sys.executable, "EXTRA": "from env"})
    launch["working_directory"].push_value(str(tmp_path))

    stage.crawler.start()

    assert action["response"].pull_value() == [
        sys.executable,
        "from env",
        os.path.realpath(tmp_path),
    ]


def test_a_given_client_name_is_used(bridge_server):
    stage, launch, _, _ = build_stage(CLIENT_COMMAND, "result = 1")
    launch["client_name"].push_value("my-launched-client")

    stage.crawler.start()

    assert launch["client"].pull_value() == "my-launched-client"


def test_every_run_gets_its_own_client_name(bridge_server):
    stage, launch, _, _ = build_stage(CLIENT_COMMAND, "result = 1")

    stage.crawler.start()
    first = launch["client"].pull_value()
    stage.crawler.start()

    assert launch["client"].pull_value() != first


def test_the_remote_client_inside_uses_the_launched_client_not_another(bridge_server):
    bystander = NyxClient(
        name="bystander",
        address=(bridge_server.host, bridge_server.port),
        token=bridge_server.token,
        reconnect=False,
    )
    bystander.start_in_thread()
    bridge_server.wait_for_client(name="bystander", timeout=5)
    stage, launch, remote, (action,) = build_stage(
        CLIENT_COMMAND, "import os\nresult = os.environ['NYX_BRIDGE_CLIENT_NAME']"
    )
    try:
        stage.crawler.start()
    finally:
        bystander.stop()

    assert remote["client"].pull_value() == launch["client"].pull_value()
    assert action["response"].pull_value() == launch["client"].pull_value()


def test_without_waiting_the_nodes_run_at_once_and_the_process_is_still_stopped(
    bridge_server,
):
    stage, launch, _, _ = build_stage(SLEEP_COMMAND, remote_client=False)
    launch["wait_for_client"].push_value(False)

    start = time.monotonic()
    stage.crawler.start()

    assert time.monotonic() - start < 10
    assert wait_until_gone(launch["process_id"].pull_value())


def test_a_process_that_ends_before_connecting_fails_with_its_output(bridge_server):
    code = "print('boom on start'); raise SystemExit(3)"
    command = f"{shlex.quote(sys.executable)} -c {shlex.quote(code)}"
    stage, _, _, _ = build_stage(command, "result = 1")

    start = time.monotonic()
    with pytest.raises(RuntimeError, match="ended before it connected") as info:
        stage.crawler.start()

    assert time.monotonic() - start < 20
    assert "exit code 3" in str(info.value) and "boom on start" in str(info.value)


def test_a_process_that_never_connects_times_out_and_is_stopped(bridge_server):
    stage, launch, _, _ = build_stage(SLEEP_COMMAND, "result = 1")
    launch["timeout"].push_value(0.5)

    start = time.monotonic()
    with pytest.raises(TimeoutError, match="did not connect"):
        stage.crawler.start()

    assert time.monotonic() - start < 20
    assert stage.crawler.context.scope_depth == 0


def test_a_program_that_does_not_exist_is_reported(bridge_server):
    stage, _, _, _ = build_stage("/no/such/program --flag", remote_client=False)

    with pytest.raises(RuntimeError, match="Could not start"):
        stage.crawler.start()


@pytest.mark.parametrize("command", ["", "   ", "echo 'unterminated"])
def test_an_empty_or_unreadable_command_is_refused(bridge_server, command):
    stage, _, _, _ = build_stage(command, remote_client=False)

    with pytest.raises(ValueError):
        stage.crawler.start()


def test_it_needs_the_bridge_server(bridge_server):
    stage, _, _, _ = build_stage(CLIENT_COMMAND, remote_client=False)
    bridge_server.stop()

    with pytest.raises(RuntimeError, match="not running"):
        stage.crawler.start()


def test_text_is_kept_as_typed_and_survives_saving(tmp_path):
    stage, launch, _, _ = build_stage("1 + 1", remote_client=False)
    assert launch["command"].pull_value() == "1 + 1"
    file_path = tmp_path / "stage.nyx"
    stage.export_json(file_path)

    other = Stage()
    STAGES.append(other)
    other.import_json(file_path)

    restored = next(
        node
        for node in other.root_node.list_children()
        if node.get_type_id() == CoreNodes.LAUNCH_PROCESS
    )
    assert restored["command"].pull_value() == "1 + 1"
    assert restored["timeout"].pull_value() == 60.0
    assert restored["process_id"].readable and not restored["process_id"].is_editable


def test_cancelling_while_the_process_boots_stops_it_and_ends_the_run(bridge_server):
    from PySide6 import QtCore

    stage, launch, _, _ = build_stage(SLEEP_COMMAND, "result = 1")
    cancelled = []
    stage.execution_cancelled.connect(lambda: cancelled.append(True))
    QtCore.QTimer.singleShot(400, stage.crawler.request_cancel)

    started = time.monotonic()
    stage.crawler.start()

    assert time.monotonic() - started < 5
    assert cancelled == [True]
    assert not stage.crawler.is_running
    assert not bridge_server.clients
    from nyx.api.v1 import NodeExecutionStatus

    assert launch.execution_status is NodeExecutionStatus.NOT_RAN


def test_events_are_processed_while_waiting_for_the_process(bridge_server):
    from PySide6 import QtCore

    # A client that takes its time, so there is a wait to process events in
    slow_code = "import time; time.sleep(0.5); " + CLIENT_CODE
    slow_command = f"{shlex.quote(sys.executable)} -c {shlex.quote(slow_code)}"
    stage, _, _, _ = build_stage(slow_command, "result = 1")
    ticks = []
    timer = QtCore.QTimer()
    timer.setInterval(20)
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start()

    stage.crawler.start()
    timer.stop()

    assert ticks
