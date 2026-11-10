import collections
import logging
import os
import shlex
import string
import subprocess
import threading
import time
import uuid

from nyx_bridge.server import BridgeServer, ClientSession
from PySide6 import QtCore

from nyx.api.v1 import (
    CoreDatatypes,
    CoreNodeComponents,
    CoreNodes,
    Node,
    NodeExecutionContext,
)

LOGGER = logging.getLogger(__name__)


class LaunchedProcess:
    """A process started by a Launch Process node, which is to connect to the bridge.

    Its output is logged line by line and the last lines are kept for error messages.
    """

    OUTPUT_LINES = 50

    def __init__(
        self,
        process: subprocess.Popen,
        client_name: str,
        server: BridgeServer,
        label: str,
    ) -> None:
        """Initialize LaunchedProcess.

        Args:
            process (subprocess.Popen): the process, with its output piped.
            client_name (str): name the process connects to the server as.
            server (BridgeServer): server the process connects to.
            label (str): shown in front of the lines of output in the log.
        """
        self.process = process
        self.client_name = client_name
        self.server = server
        self.label = label
        self.output_tail: collections.deque[str] = collections.deque(
            maxlen=self.OUTPUT_LINES
        )
        self._reader = threading.Thread(
            target=self._log_output, name=f"LaunchedProcess-{label}", daemon=True
        )
        self._reader.start()

    def _log_output(self) -> None:
        """Log the output of the process until it closes it."""
        for line in self.process.stdout:
            line = line.rstrip("\r\n")
            self.output_tail.append(line)
            LOGGER.info("[%s] %s", self.label, line)

    @property
    def is_running(self) -> bool:
        """bool: the process has not exited."""
        return self.process.poll() is None

    @property
    def session(self) -> ClientSession | None:
        """ClientSession | None: the connection of the process, None if it has none."""
        found = self.server.find_clients(name=self.client_name)
        return found[0] if found else None

    def describe_exit(self) -> str:
        """str: how the process ended, with the end of its output."""
        self._reader.join(timeout=2)
        text = f"exit code {self.process.poll()}"
        if self.output_tail:
            text += ", last output:\n" + "\n".join(self.output_tail)
        return text

    def stop(self, grace: float = 10.0, kill_after: float = 5.0) -> None:
        """Stop the process: ask its client to quit, then terminate, then kill.

        Args:
            grace (float): seconds the process gets to exit after being asked to.
            kill_after (float): seconds it gets after being terminated.
        """
        if self.is_running:
            # Only a connected client can be asked to quit, and given time to.
            session = self.session
            if session is not None:
                session.request_shutdown()
            try:
                self.process.wait(grace if session is not None else 0)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                try:
                    self.process.wait(kill_after)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
        self._reader.join(timeout=2)
        self.process.stdout.close()


class LaunchProcessNode(Node):
    """Node starting a process that connects to the bridge, for the nodes inside of it.

    Runs the command with the address and token of the bridge server, and the name
    the process is to connect as, in the environment (`NYX_BRIDGE_ADDRESS`,
    `NYX_BRIDGE_TOKEN`, `NYX_BRIDGE_CLIENT_NAME`). It waits until a client of that
    name has connected, then the nodes inside of it run. The process is stopped when
    they are done. A Remote Client inside of it uses that client, unless it is told
    another.
    """

    DEFAULT_NAME = "launch_process"
    DEFAULT_TIMEOUT = 60.0
    ADDRESS_VARIABLE = "NYX_BRIDGE_ADDRESS"
    TOKEN_VARIABLE = "NYX_BRIDGE_TOKEN"
    CLIENT_NAME_VARIABLE = "NYX_BRIDGE_CLIENT_NAME"
    POLL_INTERVAL = 0.25

    @classmethod
    def get_type_id(cls) -> str:
        """str: node type id."""
        return CoreNodes.LAUNCH_PROCESS

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return "Launch Process"

    @classmethod
    def get_type_icon(cls) -> str:
        """str: resource path of the type icon."""
        return ":core/icons/launch"

    @classmethod
    def get_description(cls) -> str:
        """str: what the node type does, shown in the palette."""
        return (
            "Starts a process that connects to the bridge server, like a headless "
            "application, waits for it and stops it when the nodes inside are done."
        )

    @classmethod
    def get_tags(cls) -> set[str]:
        """set[str]: node tags."""
        return {"bridge", "scope"}

    def setup(self) -> None:
        """Add the flow, the inputs describing the process and the outputs."""
        self._launched: LaunchedProcess | None = None

        self.flow_cpnt = self.components_model.create_component(CoreNodeComponents.FLOW)
        self.flow_cpnt.name = "flow"
        self.flow_cpnt.readable = True
        self.flow_cpnt.writable = True

        self.command_cpnt = self._create_input(
            "command",
            "Command line to run. $NAME and ${NAME} are replaced by environment "
            "variables, the ones of `env` included.",
            CoreDatatypes.STRING,
            "",
            literal=True,
        )
        self.env_cpnt = self._create_input(
            "env",
            "Environment variables added to the ones of the application.",
            CoreDatatypes.DICT,
            {},
        )
        self.working_directory_cpnt = self._create_input(
            "working_directory",
            "Folder to run the command in. Empty uses the current one.",
            CoreDatatypes.STRING,
            "",
            literal=True,
        )
        self.client_name_cpnt = self._create_input(
            "client_name",
            "Name the process is to connect to the bridge as. Empty makes one up.",
            CoreDatatypes.STRING,
            "",
            literal=True,
        )
        self.wait_cpnt = self._create_input(
            "wait_for_client",
            "Wait until the process has connected before the nodes inside run.",
            CoreDatatypes.BOOL,
            True,
        )
        self.timeout_cpnt = self._create_input(
            "timeout",
            "Seconds to wait for the process to connect before failing. 0 or less "
            "waits forever.",
            CoreDatatypes.FLOAT,
            self.DEFAULT_TIMEOUT,
        )
        self.client_cpnt = self._create_output(
            "client", "Name the process connects as.", CoreDatatypes.STRING
        )
        self.process_id_cpnt = self._create_output(
            "process_id", "Id of the process.", CoreDatatypes.INT
        )

        for component in (
            self.flow_cpnt,
            self.command_cpnt,
            self.env_cpnt,
            self.working_directory_cpnt,
            self.client_name_cpnt,
            self.wait_cpnt,
            self.timeout_cpnt,
            self.client_cpnt,
            self.process_id_cpnt,
        ):
            self.components_model.add_component(component)

    def _create_input(self, name, description, datatype, default, literal=False):
        """Create an editable input component.

        Args:
            name (str): component name.
            description (str): component description.
            datatype (str): datatype id.
            default (Any): initial value.
            literal (bool): keep text as typed instead of evaluating it.

        Returns:
            NodeComponent: new component, not added to the node yet.
        """
        component = self.components_model.create_component(CoreNodeComponents.VALUE)
        component.name = name
        component.description = description
        component.is_editable = True
        component.writable = True
        component.is_literal = literal
        component.set_datatype(datatype)
        component.push_value(default)
        return component

    def _create_output(self, name, description, datatype):
        """Create a read-only output component.

        Args:
            name (str): component name.
            description (str): component description.
            datatype (str): datatype id.

        Returns:
            NodeComponent: new component, not added to the node yet.
        """
        component = self.components_model.create_component(CoreNodeComponents.VALUE)
        component.name = name
        component.description = description
        component.readable = True
        component.is_editable = False
        component.set_datatype(datatype)
        return component

    def pre_execution_hook(self) -> None:
        """Forget the process of the previous run."""
        self._launched = None
        self.client_cpnt.push_value("", evaluate=False)
        self.process_id_cpnt.push_value(0, evaluate=False)

    def execute(self) -> None:
        """Start the process and wait for it to connect.

        Raises:
            RuntimeError: the bridge server is not running, the process could not
                be started, or it ended before it connected.
            ValueError: the command is empty or can't be split into arguments.
            TimeoutError: the process did not connect in time.
        """
        session = getattr(QtCore.QCoreApplication.instance(), "session", None)
        server = session.bridge_server if session is not None else None
        if server is None or not server.is_running:
            raise RuntimeError("The bridge server is not running")

        client_name = (
            self.client_name_cpnt.pull_value() or f"launched-{uuid.uuid4().hex[:8]}"
        )
        environment = self._build_environment(server, client_name)
        arguments = self._build_arguments(environment)
        try:
            process = subprocess.Popen(
                arguments,
                env=environment,
                cwd=self.working_directory_cpnt.pull_value() or None,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except OSError as err:
            raise RuntimeError(f"Could not start {arguments[0]!r}: {err}") from err

        self._launched = LaunchedProcess(process, client_name, server, self.name)
        LOGGER.info("%s | Started %s (process %s)", self, arguments[0], process.pid)
        try:
            if self.wait_cpnt.pull_value():
                self._wait_for_client()
        except BaseException:
            self._launched.stop(grace=0)
            raise
        self.client_cpnt.push_value(client_name, evaluate=False)
        self.process_id_cpnt.push_value(process.pid, evaluate=False)

    def _build_environment(self, server: BridgeServer, client_name: str) -> dict:
        """Get the environment of the process.

        Args:
            server (BridgeServer): the server the process is to connect to.
            client_name (str): name the process is to connect as.

        Returns:
            dict: the environment of the application, the bridge settings and `env`.
        """
        environment = dict(os.environ)
        environment[self.ADDRESS_VARIABLE] = f"{server.host}:{server.port}"
        environment[self.TOKEN_VARIABLE] = server.token
        environment[self.CLIENT_NAME_VARIABLE] = client_name
        environment.update(
            {
                str(key): str(value)
                for key, value in (self.env_cpnt.pull_value() or {}).items()
            }
        )
        return environment

    def _build_arguments(self, environment: dict) -> list[str]:
        """Split the command into arguments and expand the variables in them.

        Args:
            environment (dict): variables the arguments may name.

        Raises:
            ValueError: the command is empty or can't be split.

        Returns:
            list[str]: the arguments, the first one is the program.
        """
        command = self.command_cpnt.pull_value() or ""
        try:
            parts = shlex.split(command)
        except ValueError as err:
            raise ValueError(f"{self.name}: cannot read the command: {err}") from err
        if not parts:
            raise ValueError(f"{self.name}: no command set")
        return [string.Template(part).safe_substitute(environment) for part in parts]

    def _wait_for_client(self) -> None:
        """Wait until the process has connected, or fail when it can't.

        Raises:
            RuntimeError: the process ended before it connected.
            TimeoutError: the process did not connect in time.
        """
        launched = self._launched
        timeout = self.timeout_cpnt.pull_value()
        deadline = time.monotonic() + timeout if timeout and timeout > 0 else None
        while True:
            try:
                launched.server.wait_for_client(
                    name=launched.client_name, timeout=self.POLL_INTERVAL
                )
                return
            except TimeoutError:
                pass
            if not launched.is_running:
                raise RuntimeError(
                    f"{self.name}: the process ended before it connected as "
                    f"{launched.client_name!r}: {launched.describe_exit()}"
                )
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError(
                    f"{self.name}: the process did not connect as "
                    f"{launched.client_name!r} within {timeout}s"
                )

    def enter_scope(self, context: NodeExecutionContext) -> None:
        """Give the process to the nodes inside, and stop it when they are done.

        Args:
            context (NodeExecutionContext): context of the crawl.
        """
        launched = self._launched
        if launched is None:
            return
        context.provide(launched)
        context.add_cleanup(launched.stop)
