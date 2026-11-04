from PySide6 import QtCore

from nyx_bridge.server import BridgeServer, ClientSession

from nyx.api.v1 import (
    Node,
    NodeExecutionContext,
    CoreNodes,
    CoreNodeComponents,
    CoreDatatypes,
)


class RemoteClientNode(Node):
    """Node connecting its children to a client of a bridge server.

    Waits for a matching external process (Blender, Maya, ...) to be connected to one
    of the servers of the application, then lets the nodes inside of it send code to
    that process, see `RemoteActionNode`.
    """

    DEFAULT_NAME = "remote_client"
    DEFAULT_TIMEOUT = 30.0

    @classmethod
    def get_type_id(cls) -> str:
        """str: node type id."""
        return CoreNodes.REMOTE_CLIENT

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return "Remote Client"

    @classmethod
    def get_type_icon(cls) -> str:
        """str: resource path of the type icon."""
        return ":/icons/remote_client"

    @classmethod
    def get_description(cls) -> str:
        """str: what the node type does, shown in the palette."""
        return (
            "Waits for an external process to connect to a server, and lets the nodes "
            "inside of it run code in that process."
        )

    @classmethod
    def get_tags(cls) -> set[str]:
        """set[str]: node tags."""
        return {"bridge", "scope"}

    def setup(self) -> None:
        """Add the flow, the inputs selecting the client and the client name output."""
        self._client_session: ClientSession | None = None

        self.flow_cpnt = self.components_model.create_component(CoreNodeComponents.FLOW)
        self.flow_cpnt.name = "flow"
        self.flow_cpnt.readable = True
        self.flow_cpnt.writable = True

        self.server_cpnt = self._create_input(
            "server",
            "Name of the server to wait on. Can be empty if the application has "
            "only one.",
            CoreDatatypes.STRING,
            "",
        )
        self.client_name_cpnt = self._create_input(
            "client_name",
            "Name of the client to wait for. Empty accepts any.",
            CoreDatatypes.STRING,
            "",
        )
        self.client_kind_cpnt = self._create_input(
            "client_kind",
            'Kind of the client to wait for, like "maya". Empty accepts any.',
            CoreDatatypes.STRING,
            "",
        )
        self.timeout_cpnt = self._create_input(
            "timeout",
            "Seconds to wait for the client before failing. 0 or less waits forever.",
            CoreDatatypes.FLOAT,
            self.DEFAULT_TIMEOUT,
        )

        self.client_cpnt = self.components_model.create_component(
            CoreNodeComponents.VALUE
        )
        self.client_cpnt.name = "client"
        self.client_cpnt.description = "Name of the connected client."
        self.client_cpnt.readable = True
        self.client_cpnt.is_editable = False
        self.client_cpnt.set_datatype(CoreDatatypes.STRING)

        self.components_model.add_component(self.flow_cpnt)
        for component in (
            self.server_cpnt,
            self.client_name_cpnt,
            self.client_kind_cpnt,
            self.timeout_cpnt,
            self.client_cpnt,
        ):
            self.components_model.add_component(component)

    def _create_input(self, name: str, description: str, datatype: str, default):
        """Create an editable input value component.

        Args:
            name (str): component name.
            description (str): component description.
            datatype (str): datatype id.
            default (Any): initial value.

        Returns:
            NodeComponent: new component, not added to the node yet.
        """
        component = self.components_model.create_component(CoreNodeComponents.VALUE)
        component.name = name
        component.description = description
        component.is_editable = True
        component.writable = True
        component.set_datatype(datatype)
        component.push_value(default)
        return component

    def pre_execution_hook(self) -> None:
        """Forget the client of the previous run."""
        self._client_session = None
        self.client_cpnt.push_value("", evaluate=False)

    def _find_server(self) -> BridgeServer:
        """Find the server to wait on among the servers of the application.

        Raises:
            RuntimeError: there is no application session.
            LookupError: no such server, or no name given and not exactly one server.

        Returns:
            BridgeServer: server.
        """
        session = getattr(QtCore.QCoreApplication.instance(), "session", None)
        if session is None:
            raise RuntimeError("No application session to find bridge servers in")

        name = self.server_cpnt.pull_value()
        if name:
            server = session.bridge_servers.get_server(name)
            if server is None:
                raise LookupError(f"No bridge server named {name!r}")
            return server

        servers = session.bridge_servers.servers
        if len(servers) != 1:
            raise LookupError(
                f"Choose a server, the application has {len(servers)} bridge servers"
            )
        return servers[0]

    def execute(self) -> None:
        """Wait for the client.

        Raises:
            TimeoutError: no matching client connected in time.
        """
        server = self._find_server()
        timeout = self.timeout_cpnt.pull_value()
        try:
            self._client_session = server.wait_for_client(
                name=self.client_name_cpnt.pull_value() or None,
                kind=self.client_kind_cpnt.pull_value() or None,
                timeout=timeout if timeout and timeout > 0 else None,
            )
        except TimeoutError as err:
            raise TimeoutError(
                f"No matching client connected to {server.name!r} within {timeout}s"
            ) from err
        self.client_cpnt.push_value(self._client_session.name, evaluate=False)

    def enter_scope(self, context: NodeExecutionContext) -> None:
        """Provide the client to the nodes inside.

        Args:
            context (NodeExecutionContext): context of the crawl.
        """
        if self._client_session is not None:
            context.provide(self._client_session)
